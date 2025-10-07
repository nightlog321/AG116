import React, { useState, useEffect, useRef, useMemo, useCallback } from 'react';
import { View, Text, StyleSheet, ScrollView, TouchableOpacity, Alert, SafeAreaView, StatusBar, TextInput, KeyboardAvoidingView, Platform } from 'react-native';
import { Ionicons } from '@expo/vector-icons';
import { LinearGradient } from 'expo-linear-gradient';
import * as DocumentPicker from 'expo-document-picker';

const EXPO_PUBLIC_BACKEND_URL = process.env.EXPO_PUBLIC_BACKEND_URL;

// Modern aesthetic color palette with white/grey base and vibrant accents
const colors = {
  // Clean white/grey foundation
  background: '#ffffff',
  surface: '#f8fafc',        // Softer light grey
  surfaceElevated: '#f1f5f9', // Elevated surfaces
  border: '#e2e8f0',         // Subtle borders
  borderLight: '#f1f5f9',
  
  // Modern text hierarchy
  text: '#1e293b',           // Rich dark text
  textSecondary: '#64748b',   // Medium grey
  textMuted: '#94a3b8',      // Light grey
  textLight: '#cbd5e1',      // Very light grey
  
  // Vibrant gradient primary (Blue to Teal)
  primary: '#3b82f6',        // Bright blue
  primaryDark: '#2563eb',    // Darker blue
  primaryLight: '#dbeafe',   // Light blue tint
  primaryGradient: ['#3b82f6', '#06b6d4'], // Blue to Teal gradient
  
  // Success with modern green
  success: '#10b981',        // Emerald green
  successDark: '#059669',
  successLight: '#d1fae5',
  
  // Warning with warm amber
  warning: '#f59e0b',        // Amber
  warningDark: '#d97706',
  warningLight: '#fef3c7',
  
  // Error with modern red
  error: '#ef4444',          // Red
  errorDark: '#dc2626',
  errorLight: '#fef2f2',
  
  // Vibrant accent colors for variety
  accent: '#8b5cf6',         // Purple accent
  accentLight: '#f3f4f6',
  coral: '#ff6b6b',          // Coral accent
  coralLight: '#ffe0e0',
  teal: '#14b8a6',          // Teal accent
  tealLight: '#ccfbf1',
  
  // Shadow and depth colors
  shadow: '#1e293b',
  shadowLight: '#64748b',
};

// Types
interface Player {
  id: string;
  name: string;
  category: string;
  sitNextRound: boolean;
  sitCount: number;
  missDueToCourtLimit: number;
  isActive: boolean;  // Can be toggled for daily sessions
  // DUPR-style rating fields
  rating: number;
  matchesPlayed: number;
  wins: number;
  losses: number;
  recentForm: string[];
  ratingHistory: Array<{
    date: string;
    oldRating: number;
    newRating: number;
    change: number;
    matchId: string;
    result: string;
  }>;
  lastUpdated: string;
  stats: {
    wins: number;
    losses: number;
    pointDiff: number;
  };
}

interface Category {
  id: string;
  name: string;
  description?: string;
}

interface Match {
  id: string;
  roundIndex: number;
  courtIndex: number;
  category: string;
  teamA: string[];
  teamB: string[];
  status: 'pending' | 'active' | 'buffer' | 'done' | 'saved';
  matchType: 'singles' | 'doubles';
  scoreA?: number;
  scoreB?: number;
  matchDate: string;  // ISO date string when match was created
}

interface SessionConfig {
  numCourts: number;
  playSeconds: number;
  bufferSeconds: number;
  allowSingles: boolean;
  allowDoubles: boolean;
  allowCrossCategory: boolean;
  maximizeCourtUsage: boolean;
}

interface SessionState {
  id: string;
  currentRound: number;
  phase: 'idle' | 'play' | 'buffer' | 'ended';
  timeRemaining: number;
  paused: boolean;
  config: SessionConfig;
  histories: any;
}

// Enhanced Audio Context for horns and alerts
let audioContext: AudioContext | null = null;
let oneMinuteWarningPlayed = false;

const initializeAudio = () => {
  if (!audioContext) {
    audioContext = new (window.AudioContext || (window as any).webkitAudioContext)();
    if (audioContext.state === 'suspended') {
      audioContext.resume();
    }
  }
};

const playHorn = (type: 'start' | 'end' | 'manual' | 'warning') => {
  initializeAudio();
  if (!audioContext) return;

  const oscillator = audioContext.createOscillator();
  const gainNode = audioContext.createGain();
  
  oscillator.connect(gainNode);
  gainNode.connect(audioContext.destination);

  // Different sounds for different horns
  if (type === 'start') {
    // Inspiring start horn (rising tones)
    oscillator.frequency.setValueAtTime(220, audioContext.currentTime);
    oscillator.frequency.exponentialRampToValueAtTime(440, audioContext.currentTime + 0.5);
    oscillator.frequency.exponentialRampToValueAtTime(660, audioContext.currentTime + 1);
    gainNode.gain.setValueAtTime(0.3, audioContext.currentTime);
    gainNode.gain.exponentialRampToValueAtTime(0.01, audioContext.currentTime + 1.2);
    oscillator.start(audioContext.currentTime);
    oscillator.stop(audioContext.currentTime + 1.2);
  } else if (type === 'end') {
    // Shocking end horn (descending harsh tone)
    oscillator.frequency.setValueAtTime(880, audioContext.currentTime);
    oscillator.frequency.exponentialRampToValueAtTime(220, audioContext.currentTime + 1.5);
    oscillator.type = 'square';
    gainNode.gain.setValueAtTime(0.4, audioContext.currentTime);
    gainNode.gain.exponentialRampToValueAtTime(0.01, audioContext.currentTime + 1.8);
    oscillator.start(audioContext.currentTime);
    oscillator.stop(audioContext.currentTime + 1.8);
  } else if (type === 'warning') {
    // One-minute warning siren (urgent oscillating tone)
    oscillator.frequency.setValueAtTime(600, audioContext.currentTime);
    oscillator.frequency.exponentialRampToValueAtTime(800, audioContext.currentTime + 0.3);
    oscillator.frequency.exponentialRampToValueAtTime(600, audioContext.currentTime + 0.6);
    oscillator.frequency.exponentialRampToValueAtTime(800, audioContext.currentTime + 0.9);
    oscillator.type = 'triangle';
    gainNode.gain.setValueAtTime(0.25, audioContext.currentTime);
    gainNode.gain.exponentialRampToValueAtTime(0.01, audioContext.currentTime + 1.2);
    oscillator.start(audioContext.currentTime);
    oscillator.stop(audioContext.currentTime + 1.2);
  } else {
    // Manual horn (double beep)
    oscillator.frequency.value = 440;
    gainNode.gain.setValueAtTime(0.3, audioContext.currentTime);
    gainNode.gain.exponentialRampToValueAtTime(0.01, audioContext.currentTime + 0.3);
    oscillator.start(audioContext.currentTime);
    oscillator.stop(audioContext.currentTime + 0.3);
    
    // Second beep
    setTimeout(() => {
      const osc2 = audioContext!.createOscillator();
      const gain2 = audioContext!.createGain();
      osc2.connect(gain2);
      gain2.connect(audioContext!.destination);
      osc2.frequency.value = 440;
      gain2.gain.setValueAtTime(0.3, audioContext!.currentTime);
      gain2.gain.exponentialRampToValueAtTime(0.01, audioContext!.currentTime + 0.3);
      osc2.start(audioContext!.currentTime);
      osc2.stop(audioContext!.currentTime + 0.3);
    }, 400);
  }
};

// CSV Processing Functions
const parseCSVLine = (line: string): string[] => {
  const result: string[] = [];
  let current = '';
  let inQuotes = false;
  
  for (let i = 0; i < line.length; i++) {
    const char = line[i];
    if (char === '"') {
      inQuotes = !inQuotes;
    } else if (char === ',' && !inQuotes) {
      result.push(current.trim());
      current = '';
    } else {
      current += char;
    }
  }
  
  result.push(current.trim());
  return result;
};

const parseCSV = (csvText: string) => {
  const lines = csvText.trim().split('\n');
  const headers = parseCSVLine(lines[0]).map(h => h.toLowerCase());
  
  const players: Array<{name: string, category: string, date?: string}> = [];
  
  for (let i = 1; i < lines.length; i++) {
    const values = parseCSVLine(lines[i]);
    if (values.length >= 2) {
      const player: any = {};
      
      // Map headers to values
      headers.forEach((header, index) => {
        const value = values[index]?.replace(/"/g, '').trim();
        if (header.includes('name')) {
          player.name = value;
        } else if (header.includes('level') || header.includes('category')) {
          player.category = value;
        } else if (header.includes('rating')) {
          player.rating = parseFloat(value) || 3.0; // Default to 3.0 if invalid
        } else if (header.includes('date')) {
          player.date = value;
        }
      });
      
      if (player.name && player.category) {
        players.push(player);
      }
    }
  }
  
  return players;
};

const generateCSV = (matches: Match[], players: Player[]) => {
  let csv = 'Round,Court,Category,TeamA_Player1,TeamA_Player2,TeamB_Player1,TeamB_Player2,ScoreA,ScoreB,Status\n';
  
  // Add matches
  matches.forEach(match => {
    const teamA1 = players.find(p => p.id === match.teamA[0])?.name || '';
    const teamA2 = match.teamA[1] ? players.find(p => p.id === match.teamA[1])?.name || '' : '';
    const teamB1 = players.find(p => p.id === match.teamB[0])?.name || '';
    const teamB2 = match.teamB[1] ? players.find(p => p.id === match.teamB[1])?.name || '' : '';
    
    csv += `${match.roundIndex},${match.courtIndex + 1},${match.category},"${teamA1}","${teamA2}","${teamB1}","${teamB2}",${match.scoreA || ''},${match.scoreB || ''},${match.status}\n`;
  });
  
  // Add player stats section
  csv += '\nPLAYER STATS\n';
  csv += 'Name,Category,Wins,Losses,PointDiff,Sits,MissedDueToCourts\n';
  
  players.forEach(player => {
    csv += `"${player.name}",${player.category},${player.stats.wins},${player.stats.losses},${player.stats.pointDiff},${player.sitCount},${player.missDueToCourtLimit}\n`;
  });
  
  return csv;
};

export default function PickleballManager() {
  const [activeTab, setActiveTab] = useState('admin');
  const [players, setPlayers] = useState<Player[]>([]);
  const [categories, setCategories] = useState<Category[]>([]);
  const [matches, setMatches] = useState<Match[]>([]);
  const [session, setSession] = useState<SessionState | null>(null);
  const [loading, setLoading] = useState(true);
  const timerRef = useRef<NodeJS.Timeout | null>(null);

  // Initialize data
  useEffect(() => {
    initializeApp();
  }, []);

  // Optimized timer effect - minimal operations
  useEffect(() => {
    // Cleanup function only
    return () => {
      if (timerRef.current) {
        clearInterval(timerRef.current);
        timerRef.current = null;
      }
    };
  }, []);

  // Reset warning flag when new round starts and manage timer
  useEffect(() => {
    if (session?.phase === 'play') {
      oneMinuteWarningPlayed = false;
      // Start timer countdown for play phase
      if (!session.paused && !timerRef.current) { // Only start if not already running
        startTimerCountdown();
      }
    } else if (session?.phase === 'buffer') {
      // Start timer countdown for buffer phase  
      if (!session.paused && !timerRef.current) { // Only start if not already running
        startTimerCountdown();
      }
    } else {
      // Stop timer for idle/ended/ready phases
      if (timerRef.current) {
        clearInterval(timerRef.current);
        timerRef.current = null;
      }
    }
  }, [session?.phase, session?.paused]); // Removed session?.currentRound to prevent infinite loop

  const handleTimeUp = async (currentSession: SessionState) => {
    try {
      if (currentSession.phase === 'play') {
        // Play phase ended - start buffer phase automatically
        playHorn('end');
        
        // Show notification
        Alert.alert('⏰ Round Complete', 'Starting buffer time - preparing next round...', [{ text: 'OK' }]);
        
        // Start buffer phase
        await fetch(`${EXPO_PUBLIC_BACKEND_URL}/api/session/buffer`, { method: 'POST' });
        
        // Fetch updated session
        await fetchSession();
        
      } else if (currentSession.phase === 'buffer') {
        // Buffer phase ended - prompt for next round
        await handleBufferEnd(currentSession);
      }
    } catch (error) {
      console.error('Error handling time up:', error);
      Alert.alert('Error', 'Failed to progress to next phase. Please try manually.');
    }
  };

  const handleBufferEnd = async (currentSession: SessionState) => {
    // Buffer ended - no automatic progression, wait for manual "Next Round" button click
    console.log('Buffer phase completed. Waiting for manual Next Round button click.');
  };

  const initializeApp = async () => {
    try {
      setLoading(true);
      
      // Initialize backend data
      await fetch(`${EXPO_PUBLIC_BACKEND_URL}/api/init`, {
        method: 'POST',
      });

      // Optimize: Fetch essential data first, then secondary data
      await Promise.all([
        fetchSession(), // Most important for app state
        fetchPlayers()  // Needed for main functionality
      ]);
      
      // Fetch secondary data after main data loads
      await Promise.all([
        fetchCategories(),
        fetchMatches()
      ]);
    } catch (error) {
      console.error('Error initializing app:', error);
      Alert.alert('Error', 'Failed to initialize app');
    } finally {
      setLoading(false);
    }
  };

  const fetchPlayers = async () => {
    try {
      const response = await fetch(`${EXPO_PUBLIC_BACKEND_URL}/api/players`);
      const data = await response.json();
      setPlayers(data);
    } catch (error) {
      console.error('Error fetching players:', error);
    }
  };

  const fetchCategories = async () => {
    try {
      const response = await fetch(`${EXPO_PUBLIC_BACKEND_URL}/api/categories`);
      const data = await response.json();
      setCategories(data);
    } catch (error) {
      console.error('Error fetching categories:', error);
    }
  };

  const fetchSession = async () => {
    try {
      const response = await fetch(`${EXPO_PUBLIC_BACKEND_URL}/api/session`);
      const data = await response.json();
      setSession(data);
    } catch (error) {
      console.error('Error fetching session:', error);
    }
  };

  const fetchMatches = async () => {
    try {
      // Add cache-busting parameter to ensure fresh data
      const timestamp = new Date().getTime();
      const response = await fetch(`${EXPO_PUBLIC_BACKEND_URL}/api/matches?t=${timestamp}`, {
        headers: {
          'Cache-Control': 'no-cache',
          'Pragma': 'no-cache'
        }
      });
      const data = await response.json();
      console.log('Fetched matches data:', data.map(m => ({id: m.id, status: m.status, scoreA: m.scoreA, scoreB: m.scoreB})));
      setMatches(data);
    } catch (error) {
      console.error('Error fetching matches:', error);
    }
  };

  const formatTime = (seconds: number) => {
    const mins = Math.floor(seconds / 60);
    const secs = seconds % 60;
    return `${mins.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
  };

  // Memoized computation to prevent unnecessary recalculations
  const computeRoundsPlanned = useMemo(() => {
    if (!session) return 0;
    const totalSeconds = session.config.playSeconds + session.config.bufferSeconds;
    return Math.floor(7200 / Math.max(1, totalSeconds)); // 2 hours = 7200 seconds
  }, [session]); // Only recompute when session changes

  // Timer countdown function that updates the top right timer
  const startTimerCountdown = () => {
    // Clear any existing timer
    if (timerRef.current) {
      clearInterval(timerRef.current);
      timerRef.current = null;
    }
    
    // Start countdown timer
    timerRef.current = setInterval(async () => {
      setSession(prev => {
        if (!prev || prev.timeRemaining <= 0 || prev.phase === 'idle') {
          return prev;
        }
        
        const newTimeRemaining = prev.timeRemaining - 1;
        
        // One-minute warning siren (only during play phase)
        if (prev.phase === 'play' && newTimeRemaining === 60 && !oneMinuteWarningPlayed) {
          playHorn('warning');
          oneMinuteWarningPlayed = true;
          Alert.alert('⚠️ One Minute Warning', 'One minute remaining in this round!', [{ text: 'OK' }]);
        }
        
        if (newTimeRemaining <= 0) {
          // Reset warning flag when round ends
          oneMinuteWarningPlayed = false;
          // Time's up - trigger automatic phase transition
          handleTimeUp(prev);
        }
        
        return { ...prev, timeRemaining: newTimeRemaining };
      });
    }, 1000);
  };

  // Reset timer function - stops timer and resets to play time
  const resetTimer = async () => {
    try {
      // Stop the current timer
      if (timerRef.current) {
        clearInterval(timerRef.current);
        timerRef.current = null;
      }
      
      // Reset session via backend API
      const response = await fetch(`${EXPO_PUBLIC_BACKEND_URL}/api/session/reset`, {
        method: 'POST'
      });
      
      if (response.ok) {
        // Refresh data to get the reset session state
        await fetchSession();
        await fetchPlayers();
        await fetchCategories();
        await fetchMatches();
        
        Alert.alert('Session Reset', 'Timer stopped and reset to play time');
      }
    } catch (error) {
      console.error('Error resetting timer:', error);
      Alert.alert('Error', 'Failed to reset session');
    }
  };

  // Generate matches function (without starting timer)
  const generateMatches = async () => {
    try {
      // Initialize audio on user interaction
      initializeAudio();
      
      const response = await fetch(`${EXPO_PUBLIC_BACKEND_URL}/api/session/generate-matches`, {
        method: 'POST'
      });
      
      if (response.ok) {
        // Refresh data to get the updated session state
        await fetchSession();
        await fetchPlayers();
        await fetchCategories();
        await fetchMatches();
        
        Alert.alert('Matches Generated!', 'Players can now see their court assignments. Go to Courts tab and click "Let\'s Play" when ready.');
      }
    } catch (error) {
      console.error('Error generating matches:', error);
      Alert.alert('Error', 'Failed to generate matches');
    }
  };

  // Start session function (just starts timer)
  const nextRound = async () => {
    if (!session) return;
    
    try {
      const response = await fetch(`${EXPO_PUBLIC_BACKEND_URL}/api/session/next-round`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' }
      });
      
      if (response.ok) {
        Alert.alert('✅ Round Ready', `Round ${session.currentRound + 1} is ready! Check courts and click "Let's Play" when ready.`);
        // Refresh all data
        await Promise.all([fetchSession(), fetchPlayers(), fetchMatches()]);
      } else {
        Alert.alert('Error', 'Failed to generate next round');
      }
    } catch (error) {
      console.error('Error generating next round:', error);
      Alert.alert('Error', 'Failed to generate next round');
    }
  };

  // Player management functions
  const togglePlayerActiveStatus = async (playerId: string, playerName: string, currentStatus: boolean) => {
    try {
      const response = await fetch(`${EXPO_PUBLIC_BACKEND_URL}/api/players/${playerId}/toggle-active`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' }
      });
      
      if (response.ok) {
        const result = await response.json();
        const action = currentStatus ? 'removed from' : 'added to';
        Alert.alert('Success', `${playerName} ${action} today's session`);
        await fetchPlayers(); // Refresh player list
      } else {
        Alert.alert('Error', 'Failed to update player status');
      }
    } catch (error) {
      console.error('Error toggling player status:', error);
      Alert.alert('Error', 'Failed to update player status');
    }
  };

  const permanentlyDeletePlayer = async (playerId: string, playerName: string) => {
    Alert.alert(
      '⚠️ Permanent Delete', 
      `Are you sure you want to permanently delete ${playerName}? This will remove all their historical data and cannot be undone.`,
      [
        { text: 'Cancel', style: 'cancel' },
        { 
          text: 'Delete Forever', 
          style: 'destructive',
          onPress: async () => {
            try {
              const response = await fetch(`${EXPO_PUBLIC_BACKEND_URL}/api/players/${playerId}`, {
                method: 'DELETE'
              });
              
              if (response.ok) {
                Alert.alert('Deleted', `${playerName} has been permanently deleted`);
                await fetchPlayers(); // Refresh player list
              } else {
                Alert.alert('Error', 'Failed to delete player');
              }
            } catch (error) {
              console.error('Error deleting player:', error);
              Alert.alert('Error', 'Failed to delete player');
            }
          }
        }
      ]
    );
  };

  // Start session function (just starts timer)
  const startSession = async () => {
    try {
      // Initialize audio on user interaction
      initializeAudio();
      
      const response = await fetch(`${EXPO_PUBLIC_BACKEND_URL}/api/session/start`, {
        method: 'POST'
      });
      
      if (response.ok) {
        playHorn('start');
        
        // Refresh data to get the updated session state
        await fetchSession();
        await fetchPlayers();
        await fetchCategories();
        await fetchMatches();
        
        // Timer will be started automatically by useEffect when session phase changes to 'play'
      }
    } catch (error) {
      console.error('Error starting session:', error);
      Alert.alert('Error', 'Failed to start session');
    }
  };

  // CSV Import Function
  const importCSV = async () => {
    try {
      console.log('🔄 Import CSV button clicked!');
      Alert.alert('Import Started', 'Starting CSV import process...');
      
      // Check if we're running in a web browser
      if (Platform.OS === 'web') {
        console.log('📱 Running on web platform');
        // For web, use HTML file input
        const input = document.createElement('input');
        input.type = 'file';
        input.accept = '.csv,text/csv';
        input.onchange = async (event: any) => {
          const file = event.target.files[0];
          if (file) {
            console.log('📁 File selected:', file.name, file.size, file.type);
            Alert.alert('Processing', `Reading file: ${file.name}`);
            
            try {
              const csvText = await file.text();
              console.log('📄 CSV Text Length:', csvText.length);
              
              await processCSVData(csvText, file.name);
            } catch (error) {
              console.error('❌ Error reading file:', error);
              Alert.alert('Import Failed', `Could not read file: ${error}`);
            }
          }
        };
        input.click();
      } else {
        console.log('📱 Running on mobile platform');
        // For mobile, use expo-document-picker
        const result = await DocumentPicker.getDocumentAsync({
          type: ['text/csv', 'application/vnd.ms-excel', 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'],
          copyToCacheDirectory: true,
        });

        if (result.type === 'cancel') {
          Alert.alert('Import Cancelled', 'No file selected');
          return;
        }

        console.log('📁 File selected:', result.name, result.size, result.type);

        if (result.type === 'success') {
          // Check if it's an Excel file
          if (result.name?.endsWith('.xlsx') || result.name?.endsWith('.xls')) {
            Alert.alert(
              'Excel File Detected', 
              `File: ${result.name}\n\nPlease convert your Excel file to CSV format first. You can do this by opening the file in Excel and using "Save As" → "CSV (Comma delimited)".`,
              [{ text: 'OK' }]
            );
            return;
          }

          Alert.alert('Processing', `Reading file: ${result.name}`);

          try {
            const response = await fetch(result.uri);
            const csvText = await response.text();
            console.log('📄 CSV Text Length:', csvText.length);
            
            await processCSVData(csvText, result.name);
          } catch (fetchError) {
            console.error('❌ Error reading file:', fetchError);
            Alert.alert('Import Failed - File Reading Error', `Could not read the selected file: ${fetchError}`);
          }
        }
      }
    } catch (error) {
      console.error('❌ Import error:', error);
      Alert.alert('Import Failed - Unexpected Error', `An unexpected error occurred: ${error}`);
    }
  };

  const addTestData = async () => {
    try {
      Alert.alert('Adding Test Data', 'Adding sample players...');
      
      const response = await fetch(`${EXPO_PUBLIC_BACKEND_URL}/api/add-test-data`, {
        method: 'POST'
      });
      
      if (response.ok) {
        const result = await response.json();
        Alert.alert('✅ Test Data Added!', result.message + '\n\nRefreshing data...');
        await Promise.all([fetchSession(), fetchPlayers(), fetchCategories()]);
      } else {
        const errorText = await response.text();
        Alert.alert('❌ Failed to Add Test Data', errorText);
      }
    } catch (error) {
      console.error('Error adding test data:', error);
      Alert.alert('❌ Error', 'Failed to add test data');
    }
  };

  const processCSVData = async (csvText: string, fileName: string) => {
    try {
      console.log('🔍 Processing CSV data...');
      
      if (!csvText || csvText.trim().length === 0) {
        Alert.alert('Import Failed', 'The selected file appears to be empty.');
        return;
      }

      Alert.alert('Processing', 'Parsing CSV data...');
      
      const importedPlayers = parseCSV(csvText);
      
      console.log('👥 Parsed Players:', importedPlayers);
      
      if (importedPlayers.length === 0) {
        Alert.alert(
          'Import Failed - No Valid Data', 
          `No valid players found in CSV file.\n\nFile: ${fileName}\nFile preview:\n${csvText.substring(0, 150)}...\n\nRequired format:\nName,Category,Rating\nJohn,Beginner,3.2\nJane,Intermediate,4.5`,
          [{ text: 'OK' }]
        );
        return;
      }

      Alert.alert('Processing', `Found ${importedPlayers.length} players. Creating in database...`);

      // Import players with progress tracking
      let successCount = 0;
      let errorCount = 0;
      const errors: string[] = [];

      for (const player of importedPlayers) {
        try {
          console.log('➕ Creating player:', player);
          
          const response = await fetch(`${EXPO_PUBLIC_BACKEND_URL}/api/players`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
              name: player.name,
              category: player.category,
              rating: player.rating || 3.0
            })
          });

          if (response.ok) {
            successCount++;
            console.log(`✅ Created player: ${player.name}`);
          } else {
            const errorText = await response.text();
            console.error(`❌ Failed to create player ${player.name}:`, errorText);
            errorCount++;
            errors.push(`${player.name}: ${errorText}`);
          }
        } catch (error) {
          console.error(`❌ Error creating player ${player.name}:`, error);
          errorCount++;
          errors.push(`${player.name}: ${error}`);
        }
      }

      // Final result notification
      if (successCount > 0 && errorCount === 0) {
        Alert.alert(
          '✅ Import Successful!', 
          `Successfully imported ${successCount} players!\n\nRefreshing data...`,
          [{ text: 'OK' }]
        );
        await Promise.all([fetchSession(), fetchPlayers(), fetchCategories()]);
      } else if (successCount > 0 && errorCount > 0) {
        Alert.alert(
          '⚠️ Partial Import', 
          `Imported ${successCount} players successfully.\n${errorCount} failed.\n\nErrors:\n${errors.slice(0, 3).join('\n')}`,
          [{ text: 'OK' }]
        );
        await Promise.all([fetchSession(), fetchPlayers(), fetchCategories()]);
      } else {
        Alert.alert(
          '❌ Import Failed', 
          `Failed to import any players.\n\nErrors:\n${errors.slice(0, 3).join('\n')}`,
          [{ text: 'OK' }]
        );
      }
    } catch (error) {
      console.error('❌ Error processing CSV:', error);
      Alert.alert('Import Failed', `Error processing CSV data: ${error}`);
    }
  };

  // CSV Export Function
  const exportCSV = () => {
    try {
      const csvContent = generateCSV(matches, players);
      const blob = new Blob([csvContent], { type: 'text/csv' });
      const url = window.URL.createObjectURL(blob);
      
      const link = document.createElement('a');
      link.href = url;
      link.download = `courtchime-session-${new Date().toISOString().split('T')[0]}.csv`;
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      window.URL.revokeObjectURL(url);
      
      Alert.alert('Success', 'CSV exported successfully!');
    } catch (error) {
      Alert.alert('Error', 'Failed to export CSV');
    }
  };

  if (loading) {
    return (
      <SafeAreaView style={styles.container}>
        <StatusBar barStyle="light-content" backgroundColor={colors.background} />
        <View style={styles.loadingContainer}>
          <Text style={styles.loadingText}>Loading CourtChime...</Text>
        </View>
      </SafeAreaView>
    );
  }

  return (
    <SafeAreaView style={styles.container}>
      <StatusBar barStyle="light-content" backgroundColor={colors.background} />
      
      {/* Header with Gradient */}
      <LinearGradient
        colors={colors.primaryGradient}
        start={{ x: 0, y: 0 }}
        end={{ x: 1, y: 1 }}
        style={styles.header}
      >
        <Text style={styles.headerTitle}>CourtChime</Text>
        {session && (
          <View style={styles.sessionInfo}>
            <Text style={styles.sessionText}>
              Round {session.currentRound}/{computeRoundsPlanned} | {session.phase.toUpperCase()}
              {session.paused && ' (PAUSED)'}
            </Text>
            {session.timeRemaining > 0 && (
              <Text style={[
                styles.timerText,
                session.timeRemaining <= 60 && session.phase === 'play' ? styles.timerWarning : null,
                session.phase === 'idle' ? styles.timerIdle : null
              ]}>
                {formatTime(session.timeRemaining)}
              </Text>
            )}
          </View>
        )}
      </LinearGradient>

      {/* Tab Navigation */}
      <View style={styles.tabContainer}>
        <TouchableOpacity
          style={[styles.tab, activeTab === 'admin' && styles.activeTab]}
          onPress={() => setActiveTab('admin')}
        >
          <Ionicons 
            name="settings" 
            size={22} 
            color={activeTab === 'admin' ? colors.text : colors.textMuted} 
          />
          <Text style={[styles.tabText, activeTab === 'admin' && styles.activeTabText]}>
            Admin
          </Text>
        </TouchableOpacity>
        
        <TouchableOpacity
          style={[styles.tab, activeTab === 'dashboard' && styles.activeTab]}
          onPress={() => setActiveTab('dashboard')}
        >
          <Ionicons 
            name="grid" 
            size={22} 
            color={activeTab === 'dashboard' ? colors.text : colors.textMuted} 
          />
          <Text style={[styles.tabText, activeTab === 'dashboard' && styles.activeTabText]}>
            Courts
          </Text>
        </TouchableOpacity>
        
        <TouchableOpacity
          style={[styles.tab, activeTab === 'players' && styles.activeTab]}
          onPress={() => setActiveTab('players')}
        >
          <Ionicons 
            name="people" 
            size={22} 
            color={activeTab === 'players' ? colors.text : colors.textMuted} 
          />
          <Text style={[styles.tabText, activeTab === 'players' && styles.activeTabText]}>
            Standings
          </Text>
        </TouchableOpacity>
      </View>

      {/* Content */}
      <KeyboardAvoidingView 
        style={styles.keyboardContainer}
        behavior={Platform.OS === 'ios' ? 'padding' : 'height'}
      >
        <ScrollView style={styles.content}>
          {activeTab === 'admin' && (
            <AdminConsole 
              session={session}
              categories={categories}
              players={players}
              onRefresh={() => {
                fetchSession();
                fetchPlayers();
                fetchCategories();
              }}
              onImportCSV={importCSV}
              onExportCSV={exportCSV}
              onGenerateMatches={generateMatches}
              onResetTimer={resetTimer}
              onAddTestData={addTestData}
            />
          )}
          
          {activeTab === 'dashboard' && (
            <CourtsDashboard 
              session={session}
              matches={matches}
              players={players}
              onRefresh={() => {
                fetchMatches();
                fetchPlayers();
                fetchSession();
              }}
              onStartSession={startSession}
              onNextRound={nextRound}
              setMatches={setMatches}
            />
          )}
          
          {activeTab === 'players' && (
            <PlayersBoard players={players} matches={matches} />
          )}
        </ScrollView>
      </KeyboardAvoidingView>
    </SafeAreaView>
  );
}

// Admin Console Component
function AdminConsole({ 
  session, 
  categories, 
  players, 
  onRefresh,
  onImportCSV,
  onExportCSV,
  onGenerateMatches,
  onResetTimer,
  onAddTestData
}: { 
  session: SessionState | null;
  categories: Category[];
  players: Player[];
  onRefresh: () => void;
  onImportCSV: () => void;
  onExportCSV: () => void;
  onGenerateMatches: () => void;
  onResetTimer: () => void;
  onAddTestData: () => void;
}) {
  const [newPlayerName, setNewPlayerName] = useState('');
  const [selectedCategory, setSelectedCategory] = useState('');
  const [editingConfig, setEditingConfig] = useState(false);
  const [configForm, setConfigForm] = useState({
    numCourts: '6',
    playMinutes: '12',
    playSeconds: '00',
    bufferSeconds: '30',
    allowSingles: true,
    allowDoubles: true,
    allowCrossCategory: false,
    maximizeCourtUsage: false
  });

  const formatTime = (seconds: number) => {
    const mins = Math.floor(seconds / 60);
    const secs = seconds % 60;
    return `${mins.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
  };

  useEffect(() => {
    if (categories.length > 0 && !selectedCategory) {
      setSelectedCategory(categories[0].name);
    }
  }, [categories]);

  useEffect(() => {
    if (session?.config) {
      const playMins = Math.floor(session.config.playSeconds / 60);
      const playSecs = session.config.playSeconds % 60;
      setConfigForm({
        numCourts: session.config.numCourts.toString(),
        playMinutes: playMins.toString(),
        playSeconds: playSecs.toString().padStart(2, '0'),
        bufferSeconds: session.config.bufferSeconds.toString(),
        allowSingles: session.config.allowSingles ?? true,
        allowDoubles: session.config.allowDoubles ?? true,
        allowCrossCategory: session.config.allowCrossCategory || false,
        maximizeCourtUsage: session.config.maximizeCourtUsage || false
      });
    }
  }, [session]);

  const addPlayer = async () => {
    if (!newPlayerName.trim() || !selectedCategory) {
      Alert.alert('Error', 'Please enter player name and select category');
      return;
    }

    try {
      await fetch(`${EXPO_PUBLIC_BACKEND_URL}/api/players`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          name: newPlayerName.trim(),
          category: selectedCategory
        })
      });
      
      setNewPlayerName('');
      onRefresh();
    } catch (error) {
      Alert.alert('Error', 'Failed to add player');
    }
  };

  const saveConfiguration = async () => {
    if (!session) return;

    try {
      // Validate that at least one format is selected
      if (!configForm.allowSingles && !configForm.allowDoubles) {
        Alert.alert('Error', 'At least one format (Singles or Doubles) must be selected');
        return;
      }

      const playSeconds = parseInt(configForm.playMinutes) * 60 + parseInt(configForm.playSeconds);
      const bufferSeconds = parseInt(configForm.bufferSeconds);
      const numCourts = parseInt(configForm.numCourts);

      if (numCourts < 1 || numCourts > 20) {
        Alert.alert('Error', 'Number of courts must be between 1 and 20');
        return;
      }

      if (playSeconds < 60 || playSeconds > 3600) {
        Alert.alert('Error', 'Play time must be between 1 and 60 minutes');
        return;
      }

      if (bufferSeconds < 0 || bufferSeconds > 300) {
        Alert.alert('Error', 'Buffer time must be between 0 and 5 minutes');
        return;
      }

      await fetch(`${EXPO_PUBLIC_BACKEND_URL}/api/session/config`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          numCourts,
          playSeconds,
          bufferSeconds,
          allowSingles: configForm.allowSingles,
          allowDoubles: configForm.allowDoubles,
          allowCrossCategory: configForm.allowCrossCategory,
          maximizeCourtUsage: configForm.maximizeCourtUsage
        })
      });

      setEditingConfig(false);
      onRefresh();
      Alert.alert('Success', 'Configuration saved successfully!');
    } catch (error) {
      Alert.alert('Error', 'Failed to save configuration');
    }
  };

  const pauseResume = async () => {
    try {
      const endpoint = session?.paused ? 'resume' : 'pause';
      await fetch(`${EXPO_PUBLIC_BACKEND_URL}/api/session/${endpoint}`, {
        method: 'POST'
      });
      onRefresh();
    } catch (error) {
      Alert.alert('Error', 'Failed to pause/resume session');
    }
  };

  const manualHorn = async () => {
    try {
      initializeAudio();
      
      const response = await fetch(`${EXPO_PUBLIC_BACKEND_URL}/api/session/horn`, {
        method: 'POST'
      });
      
      if (response.ok) {
        const data = await response.json();
        playHorn(data.horn || 'manual');
        onRefresh();
      }
    } catch (error) {
      Alert.alert('Error', 'Failed to activate horn');
    }
  };

  if (!session) return <Text style={styles.loadingText}>Loading session...</Text>;

  return (
    <View style={styles.adminContainer}>
      {/* Session Controls */}
      <View style={styles.card}>
        <View style={styles.cardHeader}>
          <Text style={styles.cardTitle}>Session Configuration</Text>
          <TouchableOpacity 
            style={styles.editButtonLarge}
            onPress={() => {
              setEditingConfig(!editingConfig);
            }}
          >
            <Text style={styles.editButtonText}>
              {editingConfig ? 'Done' : 'Edit'}
            </Text>
          </TouchableOpacity>
        </View>
        
        {editingConfig ? (
          <View style={styles.configForm}>
            <View style={styles.configRow}>
              <Text style={styles.configLabel}>Courts:</Text>
              <TextInput
                style={styles.configInput}
                value={configForm.numCourts}
                onChangeText={(text) => setConfigForm({...configForm, numCourts: text})}
                keyboardType="numeric"
                maxLength={2}
              />
            </View>
            
            <View style={styles.configRow}>
              <Text style={styles.configLabel}>Play Time:</Text>
              <View style={styles.timeInputs}>
                <TextInput
                  style={styles.timeInput}
                  value={configForm.playMinutes}
                  onChangeText={(text) => setConfigForm({...configForm, playMinutes: text})}
                  keyboardType="numeric"
                  maxLength={2}
                  placeholder="12"
                  placeholderTextColor={colors.textMuted}
                />
                <Text style={styles.timeColon}>:</Text>
                <TextInput
                  style={styles.timeInput}
                  value={configForm.playSeconds}
                  onChangeText={(text) => setConfigForm({...configForm, playSeconds: text})}
                  keyboardType="numeric"
                  maxLength={2}
                  placeholder="00"
                  placeholderTextColor={colors.textMuted}
                />
              </View>
            </View>
            
            <View style={styles.configRow}>
              <Text style={styles.configLabel}>Buffer (sec):</Text>
              <TextInput
                style={styles.configInput}
                value={configForm.bufferSeconds}
                onChangeText={(text) => setConfigForm({...configForm, bufferSeconds: text})}
                keyboardType="numeric"
                maxLength={3}
              />
            </View>
            
            <View style={styles.configRow}>
              <Text style={styles.configLabel}>Formats:</Text>
              <View style={styles.formatCheckboxes}>
                <TouchableOpacity
                  style={[styles.checkboxButton, configForm.allowSingles && styles.checkboxButtonActive]}
                  onPress={() => setConfigForm({...configForm, allowSingles: !configForm.allowSingles})}
                >
                  <Text style={[styles.checkboxButtonText, configForm.allowSingles && styles.checkboxButtonTextActive]}>
                    Singles
                  </Text>
                </TouchableOpacity>
                <TouchableOpacity
                  style={[styles.checkboxButton, configForm.allowDoubles && styles.checkboxButtonActive]}
                  onPress={() => setConfigForm({...configForm, allowDoubles: !configForm.allowDoubles})}
                >
                  <Text style={[styles.checkboxButtonText, configForm.allowDoubles && styles.checkboxButtonTextActive]}>
                    Doubles
                  </Text>
                </TouchableOpacity>
              </View>
            </View>
            
            <View style={styles.configRow}>
              <Text style={styles.configLabel}>Cross-Category:</Text>
              <TouchableOpacity
                style={[styles.toggleButton, configForm.allowCrossCategory && styles.toggleButtonActive]}
                onPress={() => setConfigForm({...configForm, allowCrossCategory: !configForm.allowCrossCategory})}
              >
                <Text style={[styles.toggleButtonText, configForm.allowCrossCategory && styles.toggleButtonTextActive]}>
                  {configForm.allowCrossCategory ? 'Enabled' : 'Disabled'}
                </Text>
              </TouchableOpacity>
            </View>
            
            <View style={styles.configRow}>
              <Text style={styles.configLabel}>Maximize Courts:</Text>
              <TouchableOpacity
                style={[styles.toggleButton, configForm.maximizeCourtUsage && styles.toggleButtonActive]}
                onPress={() => setConfigForm({...configForm, maximizeCourtUsage: !configForm.maximizeCourtUsage})}
              >
                <Text style={[styles.toggleButtonText, configForm.maximizeCourtUsage && styles.toggleButtonTextActive]}>
                  {configForm.maximizeCourtUsage ? 'Enabled' : 'Disabled'}
                </Text>
              </TouchableOpacity>
            </View>
            
            <TouchableOpacity 
              style={styles.saveButton}
              onPress={saveConfiguration}
            >
              <Text style={styles.saveButtonText}>Save Configuration</Text>
            </TouchableOpacity>
          </View>
        ) : (
          <View style={styles.sessionStats}>
            <View style={styles.statItem}>
              <Text style={styles.statLabel}>Courts</Text>
              <Text style={styles.statValue}>{session.config.numCourts}</Text>
            </View>
            <View style={styles.statItem}>
              <Text style={styles.statLabel}>Rounds Planned</Text>
              <Text style={styles.statValue}>{Math.floor(7200 / Math.max(1, session.config.playSeconds + session.config.bufferSeconds))}</Text>
            </View>
            <View style={styles.statItem}>
              <Text style={styles.statLabel}>Format</Text>
              <Text style={styles.statValue}>
                {(() => {
                  const formats = [];
                  if (session.config.allowSingles) formats.push('Singles');
                  if (session.config.allowDoubles) formats.push('Doubles');
                  return formats.length > 0 ? formats.join(' + ') : 'None';
                })()}
              </Text>
            </View>
            <View style={styles.statItem}>
              <Text style={styles.statLabel}>Play Time</Text>
              <Text style={styles.statValue}>{formatTime(session.config.playSeconds)}</Text>
            </View>
            <View style={styles.statItem}>
              <Text style={styles.statLabel}>Buffer</Text>
              <Text style={styles.statValue}>{session.config.bufferSeconds}s</Text>
            </View>
            <View style={styles.statItem}>
              <Text style={styles.statLabel}>Cross-Category</Text>
              <Text style={styles.statValue}>{session.config.allowCrossCategory ? 'Yes' : 'No'}</Text>
            </View>
            <View style={styles.statItem}>
              <Text style={styles.statLabel}>Maximize Courts</Text>
              <Text style={styles.statValue}>{session.config.maximizeCourtUsage ? 'Yes' : 'No'}</Text>
            </View>
          </View>
        )}

        {/* Session Control Buttons */}
        <View style={styles.sessionControlButtons}>
          <TouchableOpacity 
            onPress={onGenerateMatches}
            disabled={players.length < 4 || (session && session.phase !== 'idle')}
            style={(players.length < 4 || (session && session.phase !== 'idle')) && styles.buttonDisabled}
          >
            <LinearGradient
              colors={players.length < 4 || (session && session.phase !== 'idle') 
                ? [colors.textMuted, colors.textLight] 
                : colors.primaryGradient}
              start={{ x: 0, y: 0 }}
              end={{ x: 1, y: 0 }}
              style={styles.primaryButton}
            >
              <Ionicons name="calendar" size={20} color="#ffffff" style={styles.buttonIcon} />
              <Text style={styles.buttonText}>Generate Matches</Text>
            </LinearGradient>
          </TouchableOpacity>
          
          <TouchableOpacity 
            style={[styles.secondaryButton, !session || session.phase === 'idle' ? styles.buttonDisabled : {}]}
            onPress={onResetTimer}
            disabled={!session || session.phase === 'idle'}
          >
            <Ionicons name="stop" size={20} color={colors.textSecondary} style={styles.buttonIcon} />
            <Text style={styles.secondaryButtonText}>Reset</Text>
          </TouchableOpacity>
        </View>
      </View>

      {/* CSV Import/Export */}
      <View style={styles.card}>
        <Text style={styles.cardTitle}>Data Management</Text>
        <Text style={styles.cardSubtitle}>
          Import/Export player data. CSV Format: Name, Category, Rating (optional)
        </Text>
        <Text style={styles.cardSubtitle}>
          📝 Excel files: Please convert to CSV first (Excel → Save As → CSV)
        </Text>
        
        <View style={styles.buttonRow}>
          <TouchableOpacity 
            style={styles.secondaryButton}
            onPress={onImportCSV}
          >
            <Ionicons name="cloud-upload" size={20} color={colors.primary} style={styles.buttonIcon} />
            <Text style={styles.secondaryButtonText}>Import CSV</Text>
          </TouchableOpacity>
          
          <TouchableOpacity 
            style={styles.secondaryButton}
            onPress={onExportCSV}
          >
            <Ionicons name="cloud-download" size={20} color={colors.primary} style={styles.buttonIcon} />
            <Text style={styles.secondaryButtonText}>Export CSV</Text>
          </TouchableOpacity>
        </View>
        
        <TouchableOpacity 
          onPress={onAddTestData}
        >
          <LinearGradient
            colors={[colors.accent, colors.teal]}
            start={{ x: 0, y: 0 }}
            end={{ x: 1, y: 0 }}
            style={[styles.primaryButton, { marginTop: 12 }]}
          >
            <Ionicons name="flask" size={20} color="#ffffff" style={styles.buttonIcon} />
            <Text style={styles.buttonText}>Add Test Data (12 Players)</Text>
          </LinearGradient>
        </TouchableOpacity>
        
        <Text style={styles.helpText}>
          CSV Format: Player Name, Player Level, Date (optional)
        </Text>
      </View>

      {/* Add Player */}
      <View style={styles.card}>
        <Text style={styles.cardTitle}>Add Player</Text>
        
        <View style={styles.inputGroup}>
          <Text style={styles.inputLabel}>Player Name</Text>
          <TextInput
            style={styles.textInput}
            value={newPlayerName}
            onChangeText={setNewPlayerName}
            placeholder="Enter player name"
            placeholderTextColor={colors.textMuted}
            autoCapitalize="words"
            returnKeyType="done"
          />
        </View>

        <View style={styles.inputGroup}>
          <Text style={styles.inputLabel}>Category</Text>
          <View style={styles.categoryButtons}>
            {categories.map((cat) => (
              <TouchableOpacity
                key={cat.id}
                style={[
                  styles.categoryButton,
                  selectedCategory === cat.name && styles.categoryButtonActive
                ]}
                onPress={() => setSelectedCategory(cat.name)}
              >
                <Text style={[
                  styles.categoryButtonText,
                  selectedCategory === cat.name && styles.categoryButtonTextActive
                ]}>
                  {cat.name}
                </Text>
              </TouchableOpacity>
            ))}
          </View>
        </View>

        <TouchableOpacity 
          style={[styles.primaryButton, !newPlayerName.trim() && styles.buttonDisabled]}
          onPress={addPlayer}
          disabled={!newPlayerName.trim()}
        >
          <Text style={styles.buttonText}>Add Player</Text>
        </TouchableOpacity>
      </View>

      {/* Current Players */}
      <View style={styles.card}>
        <Text style={styles.cardTitle}>Current Players ({players.length})</Text>
        {players.length === 0 ? (
          <Text style={styles.emptyText}>No players added yet</Text>
        ) : (
          <View style={styles.playersList}>
            {categories.map((category) => {
              const categoryPlayers = players.filter(p => p.category === category.name);
              if (categoryPlayers.length === 0) return null;
              
              return (
                <View key={category.id} style={styles.categorySection}>
                  <Text style={styles.categoryHeader}>{category.name} ({categoryPlayers.length})</Text>
                  {categoryPlayers.map((player) => (
                    <View key={player.id} style={[
                      styles.playerItem,
                      !player.isActive && styles.playerItemInactive
                    ]}>
                      <View style={styles.playerMainInfo}>
                        <Text style={[
                          styles.playerName,
                          !player.isActive && styles.playerNameInactive
                        ]}>
                          {player.name}
                          {!player.isActive && ' (Not Playing Today)'}
                        </Text>
                        <View style={styles.playerStats}>
                          <Text style={styles.playerStat}>W: {player.stats.wins}</Text>
                          <Text style={styles.playerStat}>L: {player.stats.losses}</Text>
                          <Text style={styles.playerStat}>Sits: {player.sitCount}</Text>
                        </View>
                      </View>
                      <View style={styles.playerActions}>
                        <TouchableOpacity
                          onPress={() => togglePlayerActiveStatus(player.id, player.name, player.isActive)}
                          style={[
                            styles.playerActionButton,
                            player.isActive ? styles.removeButton : styles.addButton
                          ]}
                        >
                          <Ionicons 
                            name={player.isActive ? "remove-circle" : "add-circle"} 
                            size={20} 
                            color="#ffffff" 
                          />
                          <Text style={styles.playerActionText}>
                            {player.isActive ? 'Remove' : 'Add'}
                          </Text>
                        </TouchableOpacity>
                        <TouchableOpacity
                          onPress={() => permanentlyDeletePlayer(player.id, player.name)}
                          style={[styles.playerActionButton, styles.deleteButton]}
                        >
                          <Ionicons name="trash" size={20} color="#ffffff" />
                          <Text style={styles.playerActionText}>Delete</Text>
                        </TouchableOpacity>
                      </View>
                    </View>
                  ))}
                </View>
              );
            })}
          </View>
        )}
      </View>
    </View>
  );
}

// Courts Dashboard Component (same structure, updated styles)
function CourtsDashboard({ 
  session, 
  matches, 
  players, 
  onRefresh,
  onStartSession,
  onNextRound,
  setMatches
}: { 
  session: SessionState | null;
  matches: Match[];
  players: Player[];
  onRefresh: () => void;
  onStartSession: () => void;
  onNextRound: () => void;
  setMatches: (matches: Match[]) => void;
}) {
  const [scoreInputs, setScoreInputs] = useState<{[matchId: string]: {scoreA: string, scoreB: string}}>({});

  const getPlayerName = (playerId: string) => {
    const player = players.find(p => p.id === playerId);
    return player ? player.name : 'Unknown Player';
  };

  const getCurrentMatches = () => {
    if (!session) return [];
    return matches.filter(m => m.roundIndex === session.currentRound);
  };

  const saveScore = async (match: Match) => {
    const scores = scoreInputs[match.id];
    if (!scores) {
      Alert.alert('Error', 'Please enter scores for both teams');
      return;
    }

    const scoreA = parseInt(scores.scoreA);
    const scoreB = parseInt(scores.scoreB);

    if (isNaN(scoreA) || isNaN(scoreB)) {
      Alert.alert('Error', 'Please enter valid numeric scores');
      return;
    }

    if (scoreA < 0 || scoreB < 0 || scoreA > 50 || scoreB > 50) {
      Alert.alert('Error', 'Scores must be between 0 and 50');
      return;
    }

    try {
      console.log('Saving score for match:', match.id, 'Current status:', match.status);
      
      const response = await fetch(`${EXPO_PUBLIC_BACKEND_URL}/api/matches/${match.id}/score`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ scoreA, scoreB })
      });

      if (response.ok) {
        const updatedMatch = await response.json();
        console.log('Score saved successfully, updated match status:', updatedMatch.status);
        
        // Immediately update the specific match in state
        setMatches(prevMatches => 
          prevMatches.map(m => 
            m.id === match.id 
              ? { ...m, status: updatedMatch.status, scoreA: updatedMatch.scoreA, scoreB: updatedMatch.scoreB }
              : m
          )
        );
        
        // Clear score inputs for this match
        setScoreInputs(prev => {
          const newInputs = { ...prev };
          delete newInputs[match.id];
          return newInputs;
        });

        // Also refresh matches data as backup
        console.log('Refreshing matches data...');
        await fetchMatches();
        console.log('Matches data refreshed');
        
        Alert.alert('Success', 'Score saved successfully!');
      } else {
        const errorData = await response.json();
        console.error('Failed to save score:', errorData);
        Alert.alert('Error', `Failed to save score: ${errorData.detail || 'Unknown error'}`);
      }
    } catch (error) {
      console.error('Error saving score:', error);
      Alert.alert('Error', 'Failed to save score');
    }
  };

  const updateScoreInput = (matchId: string, team: 'A' | 'B', value: string) => {
    setScoreInputs(prev => ({
      ...prev,
      [matchId]: {
        ...prev[matchId],
        [`score${team}`]: value
      }
    }));
  };

  if (!session) return <Text style={styles.loadingText}>Loading courts...</Text>;
  
  // Helper function to determine if Next Round button should be enabled
  const isNextRoundEnabled = () => {
    // Button is enabled ONLY when buffer phase ends (timeRemaining reaches 0)
    // Button should be DISABLED during play phase and buffer phase countdown
    return session.phase === 'buffer' && session.timeRemaining === 0;
  };

  // Next Round Button Component (visible during play and buffer phases)
  const NextRoundButton = () => {
    // Show button during play and buffer phases (when rounds are in progress)
    if (session.phase !== 'play' && session.phase !== 'buffer') {
      return null;
    }
    
    const enabled = isNextRoundEnabled();
    
    return (
      <View style={styles.nextRoundContainer}>
        <TouchableOpacity 
          onPress={onNextRound}
          disabled={!enabled}
          style={styles.nextRoundButton}
        >
          <LinearGradient
            colors={enabled ? [colors.success, colors.success] : ['#e0e0e0', '#bdbdbd']}
            start={{ x: 0, y: 0 }}
            end={{ x: 1, y: 0 }}
            style={[
              styles.nextRoundButtonGradient,
              !enabled && styles.nextRoundButtonDisabledGradient
            ]}
          >
            <Ionicons 
              name="arrow-forward" 
              size={20} 
              color={enabled ? "#ffffff" : "#888888"} 
            />
            <Text style={[
              styles.nextRoundButtonText,
              !enabled && styles.nextRoundButtonTextDisabled
            ]}>
              Next Round
            </Text>
          </LinearGradient>
        </TouchableOpacity>
      </View>
    );
  };
  
  if (session.phase === 'idle') {
    return (
      <View style={styles.dashboardContainer}>
        <View style={styles.card}>
          <Ionicons name="tennisball" size={48} color={colors.success} />
          <Text style={styles.emptyTitle}>Session Not Started</Text>
          <Text style={styles.emptyText}>
            Generate matches from the Admin tab to see court assignments
          </Text>
        </View>
      </View>
    );
  }

  if (session.phase === 'ready') {
    const currentMatches = getCurrentMatches();
    return (
      <View style={styles.dashboardContainer}>
        {/* Show court assignments */}
        <ScrollView style={styles.courtsScroll}>
          {Array.from({ length: session.config.numCourts }, (_, i) => i).map((courtIndex) => {
            const match = currentMatches.find(m => m.courtIndex === courtIndex);
            
            return (
              <View key={courtIndex} style={styles.courtCard}>
                <Text style={styles.courtTitle}>Court {courtIndex + 1}</Text>
                {match ? (
                  <View style={styles.courtMatch}>
                    <View style={styles.matchTeams}>
                      <View style={styles.team}>
                        <Text style={styles.teamLabel}>Team A:</Text>
                        {match.teamA.map(playerId => (
                          <Text key={playerId} style={styles.playerName}>
                            {getPlayerName(playerId)}
                          </Text>
                        ))}
                      </View>
                      <Text style={styles.vs}>VS</Text>
                      <View style={styles.team}>
                        <Text style={styles.teamLabel}>Team B:</Text>
                        {match.teamB.map(playerId => (
                          <Text key={playerId} style={styles.playerName}>
                            {getPlayerName(playerId)}
                          </Text>
                        ))}
                      </View>
                    </View>
                    <Text style={styles.matchType}>{match.matchType.toUpperCase()}</Text>
                  </View>
                ) : (
                  <Text style={styles.emptyCourt}>No match assigned</Text>
                )}
              </View>
            );
          })}
        </ScrollView>

        {/* Let's Play Button - only show when ready */}
        <View style={styles.readyActionContainer}>
          <Text style={styles.readyMessage}>
            ✅ Court assignments ready! Players can see their matches above.
          </Text>
          <TouchableOpacity 
            onPress={onStartSession}
          >
            <LinearGradient
              colors={[colors.success, colors.teal]}
              start={{ x: 0, y: 0 }}
              end={{ x: 1, y: 0 }}
              style={styles.letsPlayButton}
            >
              <Ionicons name="play" size={24} color="#ffffff" />
              <Text style={styles.letsPlayText}>Let's Play!</Text>
            </LinearGradient>
          </TouchableOpacity>
        </View>
      </View>
    );
  }

  const currentMatches = getCurrentMatches();
  const courts = Array.from({ length: session.config.numCourts }, (_, i) => i);
  
  return (
    <View style={styles.dashboardContainer}>
      <NextRoundButton />
      {courts.map((courtIndex) => {
        const match = currentMatches.find(m => m.courtIndex === courtIndex);
        
        return (
          <View key={courtIndex} style={styles.courtCard}>
            <View style={styles.courtHeader}>
              <Text style={styles.courtTitle}>Court {courtIndex + 1}</Text>
              {match && (
                <View style={styles.matchBadge}>
                  <Text style={styles.matchBadgeText}>{match.category}</Text>
                </View>
              )}
            </View>

            {match ? (
              <View style={styles.matchDetails}>
                <View style={styles.matchType}>
                  <Ionicons 
                    name={match.matchType === 'singles' ? 'person' : 'people'} 
                    size={16} 
                    color={colors.success} 
                  />
                  <Text style={styles.matchTypeText}>
                    {match.matchType.charAt(0).toUpperCase() + match.matchType.slice(1)}
                  </Text>
                </View>

                <View style={styles.teamsContainer}>
                  {/* Team A */}
                  <View style={styles.team}>
                    <Text style={styles.teamLabel}>Team A</Text>
                    {match.teamA.map((playerId, index) => (
                      <Text key={index} style={styles.playerNameInMatch}>
                        {getPlayerName(playerId)}
                      </Text>
                    ))}
                  </View>

                  <Text style={styles.vsText}>VS</Text>

                  {/* Team B */}
                  <View style={styles.team}>
                    <Text style={styles.teamLabel}>Team B</Text>
                    {match.teamB.map((playerId, index) => (
                      <Text key={index} style={styles.playerNameInMatch}>
                        {getPlayerName(playerId)}
                      </Text>
                    ))}
                  </View>
                </View>

                {match.status === 'saved' ? (
                  <View style={styles.finalScore}>
                    <Text style={styles.finalScoreText}>
                      Final Score: {match.scoreA} - {match.scoreB}
                    </Text>
                  </View>
                ) : (
                  <View style={styles.scoreInput}>
                    <View style={styles.scoreInputRow}>
                      <Text style={styles.scoreLabel}>Team A:</Text>
                      <TextInput
                        style={styles.scoreInputField}
                        value={scoreInputs[match.id]?.scoreA || ''}
                        onChangeText={(text) => updateScoreInput(match.id, 'A', text)}
                        keyboardType="numeric"
                        placeholder="0"
                        placeholderTextColor={colors.textMuted}
                        maxLength={2}
                      />
                      
                      <Text style={styles.scoreLabel}>Team B:</Text>
                      <TextInput
                        style={styles.scoreInputField}
                        value={scoreInputs[match.id]?.scoreB || ''}
                        onChangeText={(text) => updateScoreInput(match.id, 'B', text)}
                        keyboardType="numeric"
                        placeholder="0"
                        placeholderTextColor={colors.textMuted}
                        maxLength={2}
                      />
                    </View>
                    
                    <TouchableOpacity
                      style={styles.saveScoreButton}
                      onPress={() => saveScore(match)}
                    >
                      <Text style={styles.saveScoreButtonText}>Save Score</Text>
                    </TouchableOpacity>
                  </View>
                )}

                <View style={styles.matchStatus}>
                  <Text style={styles.matchStatusText}>
                    Status: {match.status.charAt(0).toUpperCase() + match.status.slice(1)}
                  </Text>
                </View>
              </View>
            ) : (
              <View style={styles.emptyCourt}>
                <Ionicons name="tennisball-outline" size={32} color={colors.textMuted} />
                <Text style={styles.emptyCourtText}>No match assigned</Text>
              </View>
            )}
          </View>
        );
      })}
    </View>
  );
}

// Players Board Component (same structure, updated styles)
function PlayersBoard({ players, matches }: { players: Player[]; matches: Match[] }) {
  // Sort players by rating (highest first) for standings
  const sortedPlayers = [...players].sort((a, b) => (b.rating || 3.0) - (a.rating || 3.0));
  
  const formatRecentForm = (recentForm: string[]) => {
    if (!recentForm || recentForm.length === 0) return 'No recent matches';
    return recentForm.slice(-5).join('-'); // Show last 5 results
  };
  
  const formatRating = (rating: number) => {
    return rating ? rating.toFixed(2) : '3.00';
  };
  
  const getRatingTrend = (ratingHistory: any[]) => {
    if (!ratingHistory || ratingHistory.length < 2) return null;
    const recent = ratingHistory.slice(-3); // Last 3 rating changes
    if (recent.length < 2) return null;
    
    const trend = recent[recent.length - 1].newRating - recent[0].oldRating;
    if (trend > 0.1) return 'up';
    if (trend < -0.1) return 'down';
    return 'stable';
  };
  
  const getRatingColor = (rating: number) => {
    if (rating >= 5.5) return '#FFD700'; // Gold for high ratings
    if (rating >= 4.5) return '#C0C0C0'; // Silver for good ratings  
    if (rating >= 3.5) return '#CD7F32'; // Bronze for average ratings
    return colors.textMuted; // Default for lower ratings
  };

  if (players.length === 0) {
    return (
      <View style={styles.dashboardContainer}>
        <View style={styles.card}>
          <Ionicons name="trophy" size={48} color={colors.primary} />
          <Text style={styles.emptyTitle}>No Players</Text>
          <Text style={styles.emptyText}>
            Add players from the Admin tab to get started with ratings
          </Text>
        </View>
      </View>
    );
  }

  return (
    <View style={styles.standingsContainer}>
      {/* Header */}
      <View style={styles.standingsHeader}>
        <Text style={styles.standingsTitle}>Player Ratings</Text>
      </View>
      
      {/* Standings List */}
      <ScrollView style={styles.standingsList}>
        {sortedPlayers.map((player, index) => {
          const winRate = (player.matchesPlayed || 0) > 0 
            ? ((player.wins || 0) / (player.matchesPlayed || 1) * 100).toFixed(0)
            : '0';
          const trend = getRatingTrend(player.ratingHistory || []);
          const ratingColor = getRatingColor(player.rating || 3.0);
          
          return (
            <View key={player.id} style={styles.standingRow}>
              {/* Rank */}
              <View style={styles.rankContainer}>
                <Text style={styles.rankNumber}>{index + 1}</Text>
                {index === 0 && <Ionicons name="trophy" size={16} color="#FFD700" />}
                {index === 1 && <Ionicons name="medal" size={16} color="#C0C0C0" />}
                {index === 2 && <Ionicons name="medal" size={16} color="#CD7F32" />}
              </View>
              
              {/* Player Info */}
              <View style={styles.playerInfo}>
                <Text style={styles.standingPlayerName}>{player.name}</Text>
                {/* Category Sticker */}
                <View style={[
                  styles.categorySticker, 
                  player.category === 'Beginner' && styles.categoryBeginner,
                  player.category === 'Intermediate' && styles.categoryIntermediate,
                  player.category === 'Advanced' && styles.categoryAdvanced
                ]}>
                  <Text style={[
                    styles.categoryStickerText,
                    player.category === 'Beginner' && styles.categoryBeginnerText,
                    player.category === 'Intermediate' && styles.categoryIntermediateText,
                    player.category === 'Advanced' && styles.categoryAdvancedText
                  ]}>
                    {player.category.toUpperCase()}
                  </Text>
                </View>
              </View>
              
              {/* Rating */}
              <View style={styles.ratingContainer}>
                <View style={styles.ratingBox}>
                  <Text style={[styles.ratingNumber, { color: ratingColor }]}>
                    {formatRating(player.rating || 3.0)}
                  </Text>
                  {trend && (
                    <Ionicons 
                      name={trend === 'up' ? 'trending-up' : trend === 'down' ? 'trending-down' : 'remove'} 
                      size={16} 
                      color={trend === 'up' ? '#00ff00' : trend === 'down' ? '#ff4444' : colors.textMuted}
                    />
                  )}
                </View>
              </View>
              
              {/* Stats */}
              <View style={styles.playerStats}>
                <Text style={styles.statText}>
                  {player.wins || 0}-{player.losses || 0}
                </Text>
                <Text style={styles.statSubtext}>
                  {winRate}% ({player.matchesPlayed || 0} matches)
                </Text>
                <Text style={styles.recentForm}>
                  Form: {formatRecentForm(player.recentForm || [])}
                </Text>
              </View>
            </View>
          );
        })}
      </ScrollView>
      
      {/* Legend */}
      <View style={styles.ratingsLegend}>
        <Text style={styles.legendTitle}>Rating Scale</Text>
        <View style={styles.legendRow}>
          <View style={styles.legendItem}>
            <View style={[styles.legendColor, { backgroundColor: '#FFD700' }]} />
            <Text style={styles.legendText}>5.5+ Elite</Text>
          </View>
          <View style={styles.legendItem}>
            <View style={[styles.legendColor, { backgroundColor: '#C0C0C0' }]} />
            <Text style={styles.legendText}>4.5+ Advanced</Text>
          </View>
          <View style={styles.legendItem}>
            <View style={[styles.legendColor, { backgroundColor: '#CD7F32' }]} />
            <Text style={styles.legendText}>3.5+ Intermediate</Text>
          </View>
          <View style={styles.legendItem}>
            <View style={[styles.legendColor, { backgroundColor: colors.textMuted }]} />
            <Text style={styles.legendText}>Below 3.5 Beginner</Text>
          </View>
        </View>
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: colors.background,
  },
  loadingContainer: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
  },
  loadingText: {
    color: colors.text,
    fontSize: 18,
    fontWeight: '600',
    textAlign: 'center',
  },
  header: {
    padding: 24,
    paddingBottom: 32,
    shadowColor: colors.shadow,
    shadowOffset: { width: 0, height: 4 },
    shadowOpacity: 0.15,
    shadowRadius: 12,
    elevation: 8,
  },
  headerTitle: {
    color: '#ffffff',
    fontSize: 28,
    fontWeight: '700',
    textAlign: 'center',
    letterSpacing: -0.5,
    textShadowColor: 'rgba(0, 0, 0, 0.2)',
    textShadowOffset: { width: 0, height: 1 },
    textShadowRadius: 2,
  },
  sessionInfo: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginTop: 16,
    backgroundColor: 'rgba(255, 255, 255, 0.15)',
    borderRadius: 12,
    padding: 12,
    backdropFilter: 'blur(10px)',
  },
  sessionText: {
    color: '#ffffff',
    fontSize: 15,
    fontWeight: '600',
    opacity: 0.9,
  },
  timerText: {
    color: '#ffffff',
    fontSize: 18,
    fontWeight: '700',
    letterSpacing: 0.5,
    textShadowColor: 'rgba(0, 0, 0, 0.3)',
    textShadowOffset: { width: 0, height: 1 },
    textShadowRadius: 2,
  },
  timerWarning: {
    color: colors.coral,
    textShadowColor: 'rgba(255, 107, 107, 0.5)',
  },
  timerIdle: {
    color: '#ffffff',
    opacity: 0.7,
  },
  tabContainer: {
    flexDirection: 'row',
    backgroundColor: colors.surfaceElevated,
    padding: 6,
    borderRadius: 16,
    marginHorizontal: 20,
    marginBottom: 24,
    shadowColor: colors.shadow,
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.08,
    shadowRadius: 8,
    elevation: 3,
  },
  tab: {
    flex: 1,
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    paddingVertical: 12,
    paddingHorizontal: 16,
    borderRadius: 12,
  },
  activeTab: {
    backgroundColor: colors.background,
    shadowColor: colors.primary,
    shadowOffset: { width: 0, height: 3 },
    shadowOpacity: 0.15,
    shadowRadius: 6,
    elevation: 2,
  },
  tabText: {
    fontSize: 14,
    fontWeight: '500',
    marginLeft: 6,
    color: colors.textMuted,
  },
  activeTabText: {
    color: colors.primary,
    fontWeight: '700',
  },
  content: {
    flex: 1,
  },
  keyboardContainer: {
    flex: 1,
  },
  adminContainer: {
    padding: 20,
  },
  card: {
    backgroundColor: colors.background,
    borderRadius: 16,
    padding: 24,
    marginBottom: 20,
    borderWidth: 1,
    borderColor: colors.border,
    shadowColor: colors.shadow,
    shadowOffset: { width: 0, height: 6 },
    shadowOpacity: 0.1,
    shadowRadius: 12,
    elevation: 4,
  },
  cardTitle: {
    color: colors.textDark,
    fontSize: 16,
    fontWeight: '600', // Notion uses 600 weight, not 700
    marginBottom: 12,
    letterSpacing: -0.2, // Tight spacing like Notion
  },
  cardSubtitle: {
    color: colors.textSecondary,
    fontSize: 14,
    marginBottom: 16,
    lineHeight: 20, // Better line height for readability
  },
  cardHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: 20,
  },
  editButtonLarge: {
    paddingVertical: 10,
    paddingHorizontal: 16,
    borderRadius: 8,
    backgroundColor: colors.primary,
    minWidth: 70,
  },
  editButtonText: {
    color: colors.text,
    fontSize: 14,
    fontWeight: '600',
    textAlign: 'center',
  },
  configForm: {
    gap: 20,
  },
  configRow: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
  },
  configLabel: {
    color: colors.textSecondary,
    fontSize: 14, // Notion-style smaller labels
    fontWeight: '500',
    flex: 1,
  },
  configInput: {
    color: colors.text,
    fontSize: 14,
    padding: 8, // Notion-style tighter padding
    backgroundColor: colors.background,
    borderRadius: 4, // Notion-style subtle rounding
    borderWidth: 1,
    borderColor: colors.border,
    textAlign: 'center',
    minWidth: 60, // Smaller minimum width
  },
  timeInputs: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 8,
  },
  timeInput: {
    color: colors.text,
    fontSize: 16,
    padding: 12,
    backgroundColor: colors.surfaceLight,
    borderRadius: 8,
    borderWidth: 1,
    borderColor: colors.border,
    textAlign: 'center',
    width: 50,
  },
  timeColon: {
    color: colors.text,
    fontSize: 18,
    fontWeight: '700',
  },
  toggleButton: {
    paddingVertical: 8,
    paddingHorizontal: 12,
    borderRadius: 4, // Notion-style subtle rounding
    backgroundColor: colors.background,
    borderWidth: 1,
    borderColor: colors.border,
  },
  toggleButtonActive: {
    backgroundColor: colors.accent, // Use grey accent instead of primary
    borderColor: colors.accent,
  },
  toggleButtonText: {
    color: colors.textSecondary,
    fontSize: 12, // Smaller Notion-style text
    fontWeight: '500',
    textAlign: 'center',
  },
  toggleButtonTextActive: {
    color: colors.background, // White text on active buttons
    fontWeight: '600',
  },
  saveButton: {
    backgroundColor: colors.success,
    paddingVertical: 16,
    borderRadius: 14,
    alignItems: 'center',
    marginTop: 12,
    shadowColor: colors.success,
    shadowOffset: { width: 0, height: 4 },
    shadowOpacity: 0.3,
    shadowRadius: 8,
    elevation: 5,
  },
  saveButtonText: {
    color: colors.text,
    fontSize: 16,
    fontWeight: '600',
  },
  sessionStats: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    justifyContent: 'space-between',
    marginBottom: 20,
    gap: 16,
  },
  statItem: {
    alignItems: 'center',
    minWidth: '30%',
  },
  statLabel: {
    color: colors.textSecondary,
    fontSize: 12,
    fontWeight: '500',
    marginBottom: 6,
    textTransform: 'uppercase',
    letterSpacing: 0.5,
  },
  statValue: {
    color: colors.text,
    fontSize: 18,
    fontWeight: '700',
  },
  buttonRow: {
    flexDirection: 'row',
    gap: 12,
    flexWrap: 'wrap',
  },
  sessionControlButtons: {
    flexDirection: 'row',
    gap: 16,
    marginTop: 8,
  },
  buttonColumn: {
    gap: 12,
  },
  primaryButton: {
    flex: 1,
    backgroundColor: colors.primary,
    paddingVertical: 14,
    paddingHorizontal: 20,
    borderRadius: 12,
    alignItems: 'center',
    flexDirection: 'row',
    justifyContent: 'center',
    minHeight: 48,
    shadowColor: colors.primary,
    shadowOffset: { width: 0, height: 4 },
    shadowOpacity: 0.3,
    shadowRadius: 8,
    elevation: 5,
  },
  warningButton: {
    flex: 1,
    backgroundColor: colors.warning,
    paddingVertical: 10,
    paddingHorizontal: 16,
    borderRadius: 6,
    alignItems: 'center',
    flexDirection: 'row',
    justifyContent: 'center',
    minHeight: 40,
  },
  dangerButton: {
    flex: 1,
    backgroundColor: colors.error, // Updated to use error instead of danger
    paddingVertical: 10,
    paddingHorizontal: 16,
    borderRadius: 6,
    alignItems: 'center',
    flexDirection: 'row',
    justifyContent: 'center',
    minHeight: 40,
  },
  secondaryButton: {
    flex: 1,
    backgroundColor: colors.background,
    paddingVertical: 10,
    paddingHorizontal: 16,
    borderRadius: 6,
    borderWidth: 1,
    borderColor: colors.border,
    alignItems: 'center',
    flexDirection: 'row',
    justifyContent: 'center',
    minHeight: 40,
  },
  buttonDisabled: {
    opacity: 0.4, // Notion-style opacity
  },
  buttonIcon: {
    marginRight: 6, // Tighter spacing like Notion
  },
  buttonText: {
    color: '#ffffff',
    fontSize: 15,
    fontWeight: '700',
  },
  secondaryButtonText: {
    color: colors.text, // Dark text on secondary buttons
    fontSize: 14,
    fontWeight: '600',
  },
  helpText: {
    color: colors.textMuted,
    fontSize: 12,
    textAlign: 'center',
    marginTop: 8,
    fontStyle: 'italic',
  },
  inputGroup: {
    marginBottom: 20,
  },
  inputLabel: {
    color: colors.textSecondary,
    fontSize: 14,
    fontWeight: '600',
    marginBottom: 8,
    textTransform: 'uppercase',
    letterSpacing: 0.5,
  },
  textInput: {
    backgroundColor: colors.background,
    borderWidth: 2,
    borderColor: colors.border,
    borderRadius: 14,
    padding: 18,
    fontSize: 16,
    color: colors.text,
    marginBottom: 16,
    shadowColor: colors.shadowLight,
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.06,
    shadowRadius: 6,
    elevation: 3,
  },
  categoryButtons: {
    flexDirection: 'row',
    gap: 10,
  },
  categoryButton: {
    flex: 1,
    paddingVertical: 12,
    paddingHorizontal: 16,
    borderRadius: 10,
    backgroundColor: colors.surfaceLight,
    borderWidth: 1,
    borderColor: colors.border,
    alignItems: 'center',
  },
  categoryButtonActive: {
    backgroundColor: colors.primary,
    borderColor: colors.primary,
  },
  categoryButtonText: {
    color: colors.textSecondary,
    fontSize: 14,
    fontWeight: '500',
  },
  categoryButtonTextActive: {
    color: colors.text,
    fontWeight: '600',
  },
  formatCheckboxes: {
    flexDirection: 'row',
    gap: 10,
  },
  checkboxButton: {
    flex: 1,
    paddingVertical: 10,
    paddingHorizontal: 16,
    borderRadius: 8,
    backgroundColor: colors.surfaceLight,
    borderWidth: 1,
    borderColor: colors.border,
    alignItems: 'center',
  },
  checkboxButtonActive: {
    backgroundColor: colors.accent, // Use grey accent instead of primary
    borderColor: colors.accent,
  },
  checkboxButtonText: {
    color: colors.textSecondary,
    fontSize: 14,
    fontWeight: '500',
  },
  checkboxButtonTextActive: {
    color: colors.text,
    fontWeight: '600',
  },
  emptyText: {
    color: colors.textMuted,
    fontSize: 16,
    textAlign: 'center',
    fontStyle: 'italic',
  },
  playersList: {
    gap: 16,
  },
  categorySection: {
    marginBottom: 20,
  },
  categoryHeader: {
    color: colors.success,
    fontSize: 16,
    fontWeight: '700',
    marginBottom: 12,
    textTransform: 'uppercase',
    letterSpacing: 0.5,
  },
  playerItem: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    paddingVertical: 12,
    paddingHorizontal: 16,
    backgroundColor: colors.surfaceLight,
    borderRadius: 10,
    marginBottom: 6,
  },
  playerName: {
    color: colors.text,
    fontSize: 16,
    fontWeight: '600',
    flex: 1,
  },
  playerStats: {
    flexDirection: 'row',
    gap: 16,
  },
  playerStat: {
    color: colors.textSecondary,
    fontSize: 12,
    fontWeight: '500',
  },
  dashboardContainer: {
    padding: 20,
  },
  emptyTitle: {
    color: colors.text,
    fontSize: 22,
    fontWeight: '700',
    textAlign: 'center',
    marginTop: 16,
    marginBottom: 8,
  },
  courtCard: {
    backgroundColor: colors.surface,
    borderRadius: 16,
    padding: 20,
    marginBottom: 16,
    borderWidth: 1,
    borderColor: colors.border,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.1,
    shadowRadius: 8,
    elevation: 3,
  },
  courtHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: 16,
  },
  courtTitle: {
    color: colors.text,
    fontSize: 20,
    fontWeight: '700',
  },
  matchBadge: {
    backgroundColor: colors.success,
    paddingHorizontal: 12,
    paddingVertical: 6,
    borderRadius: 16,
  },
  matchBadgeText: {
    color: colors.text,
    fontSize: 12,
    fontWeight: '700',
    textTransform: 'uppercase',
    letterSpacing: 0.5,
  },
  matchDetails: {
    gap: 16,
  },
  matchType: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 8,
  },
  matchTypeText: {
    color: colors.success,
    fontSize: 14,
    fontWeight: '600',
  },
  teamsContainer: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-around',
    backgroundColor: colors.surfaceLight,
    borderRadius: 12,
    padding: 16,
  },
  team: {
    alignItems: 'center',
    flex: 1,
  },
  teamLabel: {
    color: colors.textSecondary,
    fontSize: 12,
    marginBottom: 8,
    fontWeight: '700',
    textTransform: 'uppercase',
    letterSpacing: 0.5,
  },
  playerNameInMatch: {
    color: colors.text,
    fontSize: 16,
    fontWeight: '600',
    marginBottom: 4,
    textAlign: 'center',
  },
  vsText: {
    color: colors.success,
    fontSize: 18,
    fontWeight: '700',
    marginHorizontal: 20,
  },
  scoreInput: {
    backgroundColor: colors.surfaceLight,
    borderRadius: 12,
    padding: 16,
  },
  scoreInputRow: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    marginBottom: 16,
  },
  scoreLabel: {
    color: colors.textSecondary,
    fontSize: 14,
    fontWeight: '600',
  },
  scoreInputField: {
    backgroundColor: colors.surface,
    borderWidth: 1,
    borderColor: colors.border,
    borderRadius: 8,
    paddingHorizontal: 16,
    paddingVertical: 12,
    color: colors.text,
    fontSize: 16,
    fontWeight: '600',
    textAlign: 'center',
    minWidth: 70,
  },
  saveScoreButton: {
    backgroundColor: colors.success,
    paddingVertical: 12,
    borderRadius: 8,
    alignItems: 'center',
  },
  saveScoreButtonText: {
    color: colors.text,
    fontSize: 14,
    fontWeight: '600',
  },
  finalScore: {
    backgroundColor: colors.surfaceLight,
    borderRadius: 12,
    padding: 16,
    alignItems: 'center',
  },
  finalScoreText: {
    color: colors.success,
    fontSize: 18,
    fontWeight: '700',
  },
  matchStatus: {
    alignItems: 'center',
  },
  matchStatusText: {
    color: colors.textMuted,
    fontSize: 12,
    fontWeight: '500',
    fontStyle: 'italic',
  },
  emptyCourt: {
    alignItems: 'center',
    paddingVertical: 32,
  },
  emptyCourtText: {
    color: colors.textMuted,
    fontSize: 16,
    marginTop: 12,
  },
  playersContainer: {
    padding: 20,
  },
  playerCard: {
    backgroundColor: colors.surface,
    borderRadius: 16,
    padding: 20,
    marginBottom: 16,
    borderWidth: 1,
    borderColor: colors.border,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.1,
    shadowRadius: 8,
    elevation: 3,
  },
  playerCardName: {
    color: colors.text,
    fontSize: 20,
    fontWeight: '700',
    marginBottom: 6,
  },
  playerCardCategory: {
    color: colors.success,
    fontSize: 14,
    fontWeight: '600',
    marginBottom: 16,
  },
  playerCardStats: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    marginBottom: 12,
  },
  playerCardStat: {
    color: colors.textSecondary,
    fontSize: 12,
    fontWeight: '500',
  },
  playerAssignment: {
    color: colors.textMuted,
    fontSize: 16,
    fontWeight: '500',
    fontStyle: 'italic',
    textAlign: 'center',
    marginTop: 8,
  },
  playerAssigned: {
    color: colors.success,
    fontWeight: '600',
    fontStyle: 'normal',
  },
  // New standings styles
  standingsContainer: {
    flex: 1,
    backgroundColor: colors.background,
  },
  standingsHeader: {
    alignItems: 'center',
    paddingVertical: 20,
    borderBottomWidth: 1,
    borderBottomColor: colors.border,
    marginBottom: 16,
  },
  standingsTitle: {
    color: colors.text,
    fontSize: 24,
    fontWeight: '700',
    marginBottom: 4,
  },
  standingsSubtitle: {
    color: colors.textMuted,
    fontSize: 14,
    fontStyle: 'italic',
  },
  standingsList: {
    flex: 1,
    paddingHorizontal: 16,
  },
  standingRow: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: colors.surface,
    borderRadius: 12,
    padding: 12, // Reduced padding
    marginBottom: 8, // Reduced margin
    borderWidth: 1,
    borderColor: colors.border,
    minHeight: 70, // Reduced height
  },
  rankContainer: {
    alignItems: 'center',
    justifyContent: 'center',
    width: 40, // Further reduced
    marginRight: 8, // Reduced margin
  },
  rankNumber: {
    color: colors.text,
    fontSize: 16, // Reduced font size
    fontWeight: '700',
    marginBottom: 2, // Reduced margin
  },
  playerInfo: {
    flex: 1,
    marginRight: 8, // Reduced margin
    justifyContent: 'center',
  },
  standingPlayerName: {
    color: colors.text,
    fontSize: 14, // Reduced font size
    fontWeight: '600',
    marginBottom: 2,
    numberOfLines: 1, // Prevent text wrapping
  },
  standingPlayerCategory: {
    color: colors.textMuted,
    fontSize: 12,
    textTransform: 'uppercase',
    letterSpacing: 0.5,
  },
  ratingContainer: {
    alignItems: 'center',
    marginRight: 8, // Reduced margin
  },
  ratingBox: {
    alignItems: 'center',
    justifyContent: 'center',
    backgroundColor: colors.surfaceLight,
    borderRadius: 6, // Reduced border radius
    padding: 6, // Reduced padding
    minWidth: 45, // Further reduced
  },
  ratingNumber: {
    fontSize: 14, // Reduced font size
    fontWeight: '700',
    marginBottom: 0, // Removed margin
  },
  playerStats: {
    alignItems: 'flex-end',
    minWidth: 80, // Further reduced
    maxWidth: 90, // Reduced max width
  },
  statText: {
    color: colors.text,
    fontSize: 12, // Reduced font size
    fontWeight: '600',
    marginBottom: 1, // Reduced margin
  },
  statSubtext: {
    color: colors.textMuted,
    fontSize: 10, // Reduced font size
    marginBottom: 2, // Reduced margin
  },
  recentForm: {
    color: colors.textSecondary,
    fontSize: 9, // Reduced font size
    fontFamily: 'monospace',
  },
  ratingsLegend: {
    backgroundColor: colors.surface,
    borderTopWidth: 1,
    borderTopColor: colors.border,
    padding: 16,
    marginTop: 8,
  },
  legendTitle: {
    color: colors.text,
    fontSize: 14,
    fontWeight: '600',
    marginBottom: 12,
    textAlign: 'center',
  },
  legendRow: {
    flexDirection: 'row',
    justifyContent: 'space-around',
    flexWrap: 'wrap',
  },
  legendItem: {
    flexDirection: 'row',
    alignItems: 'center',
    marginBottom: 8,
  },
  legendColor: {
    width: 12,
    height: 12,
    borderRadius: 6,
    marginRight: 6,
  },
  legendText: {
    color: colors.textMuted,
    fontSize: 12,
    fontWeight: '500',
  },
  // Category sticker styles
  categorySticker: {
    paddingHorizontal: 4, // Reduced padding
    paddingVertical: 1, // Reduced padding
    borderRadius: 6, // Reduced border radius
    alignSelf: 'flex-start',
    marginTop: 2, // Reduced margin
    borderWidth: 1,
  },
  categoryBeginner: {
    backgroundColor: '#E8F5E8',
    borderColor: '#4CAF50',
  },
  categoryIntermediate: {
    backgroundColor: '#FFF3E0',
    borderColor: '#FF9800',
  },
  categoryAdvanced: {
    backgroundColor: '#FCE4EC',
    borderColor: '#E91E63',
  },
  categoryStickerText: {
    fontSize: 9,
    fontWeight: '600',
    letterSpacing: 0.5,
    textTransform: 'uppercase',
  },
  categoryBeginnerText: {
    color: '#2E7D32',
  },
  categoryIntermediateText: {
    color: '#F57C00',
  },
  categoryAdvancedText: {
    color: '#C2185B',
  },
  // Ready phase styles
  courtsScroll: {
    flex: 1,
    paddingHorizontal: 16,
  },
  readyActionContainer: {
    padding: 20,
    backgroundColor: colors.surface,
    borderTopWidth: 1,
    borderTopColor: colors.border,
    alignItems: 'center',
  },
  readyMessage: {
    color: colors.success,
    fontSize: 16,
    fontWeight: '600',
    textAlign: 'center',
    marginBottom: 16,
  },
  letsPlayButton: {
    paddingVertical: 18,
    paddingHorizontal: 36,
    borderRadius: 28,
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    minWidth: 220,
    shadowColor: colors.success,
    shadowOffset: { width: 0, height: 6 },
    shadowOpacity: 0.3,
    shadowRadius: 12,
    elevation: 8,
  },
  letsPlayText: {
    color: '#ffffff',
    fontSize: 19,
    fontWeight: '700',
    marginLeft: 10,
    textShadowColor: 'rgba(0, 0, 0, 0.2)',
    textShadowOffset: { width: 0, height: 1 },
    textShadowRadius: 2,
  },
  nextRoundContainer: {
    paddingHorizontal: 16,
    paddingVertical: 12,
    backgroundColor: 'rgba(255, 255, 255, 0.9)',
    borderBottomWidth: 1,
    borderBottomColor: colors.border,
  },
  nextRoundButton: {
    alignSelf: 'center',
  },
  nextRoundButtonGradient: {
    paddingVertical: 16,  // Increased from 12 to 16 for better touch target
    paddingHorizontal: 32, // Increased from 24 to 32 for better touch target
    borderRadius: 25,     // Increased from 20 to 25 for better appearance
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    minWidth: 160,        // Increased from 140 to 160
    minHeight: 48,        // Added minimum height for touch-friendly button
  },
  nextRoundButtonDisabledGradient: {
    opacity: 1, // Keep full opacity for the gradient itself
  },
  nextRoundButtonText: {
    color: '#ffffff',
    fontSize: 16,
    fontWeight: '600',
    marginLeft: 8,
  },
  nextRoundButtonTextDisabled: {
    color: '#888888', // Darker text for disabled state
  },
  // Player management styles
  playerMainInfo: {
    flex: 1,
  },
  playerActions: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 8,
    marginLeft: 12,
  },
  playerActionButton: {
    paddingVertical: 8,
    paddingHorizontal: 12,
    borderRadius: 16,
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    minWidth: 80,
  },
  playerActionText: {
    color: '#ffffff',
    fontSize: 12,
    fontWeight: '600',
    marginLeft: 4,
  },
  removeButton: {
    backgroundColor: colors.warning,
  },
  addButton: {
    backgroundColor: colors.success,
  },
  deleteButton: {
    backgroundColor: colors.danger,
  },
  playerItemInactive: {
    opacity: 0.6,
    backgroundColor: '#f5f5f5',
  },
  playerNameInactive: {
    color: colors.textMuted,
    fontStyle: 'italic',
  },
});