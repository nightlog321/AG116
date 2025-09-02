import React, { useState, useEffect, useRef } from 'react';
import { View, Text, StyleSheet, ScrollView, TouchableOpacity, Alert, SafeAreaView, StatusBar, TextInput, KeyboardAvoidingView, Platform } from 'react-native';
import { Ionicons } from '@expo/vector-icons';
import * as DocumentPicker from 'expo-document-picker';

const EXPO_PUBLIC_BACKEND_URL = process.env.EXPO_PUBLIC_BACKEND_URL;

// Modern Color Palette
const colors = {
  primary: '#667eea',      // Modern purple-blue
  primaryDark: '#5a6fd8',
  secondary: '#764ba2',    // Deep purple
  success: '#2dd4bf',      // Modern teal
  successDark: '#0f766e',
  warning: '#f59e0b',      // Warm amber
  danger: '#ef4444',       // Modern red
  background: '#0f172a',   // Deep slate
  surface: '#1e293b',      // Slate
  surfaceLight: '#334155', // Light slate
  text: '#f8fafc',         // Light text
  textSecondary: '#cbd5e1', // Muted text
  textMuted: '#64748b',    // Very muted text
  border: '#475569',       // Border color
  accent: '#06b6d4',       // Cyan accent
};

// Types
interface Player {
  id: string;
  name: string;
  category: string;
  sitNextRound: boolean;
  sitCount: number;
  missDueToCourtLimit: number;
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
  status: 'pending' | 'active' | 'buffer' | 'done';
  matchType: 'singles' | 'doubles';
  scoreA?: number;
  scoreB?: number;
}

interface SessionConfig {
  numCourts: number;
  playSeconds: number;
  bufferSeconds: number;
  allowSingles: boolean;
  allowDoubles: boolean;
  allowCrossCategory: boolean;
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

  // Timer effect - ONLY runs when explicitly started by user
  useEffect(() => {
    // DO NOT auto-start timer on app load
    // Timer should only run when:
    // 1. Session is actively in play or buffer phase
    // 2. Not paused
    // 3. Has time remaining
    // 4. User has explicitly started the session (not on app load)
    
    // We'll control timer start/stop through the startSession function instead
    // This useEffect is now just for cleanup
    return () => {
      if (timerRef.current) {
        clearInterval(timerRef.current);
        timerRef.current = null;
      }
    };
  }, []);

  // Reset warning flag when new round starts
  useEffect(() => {
    if (session?.phase === 'play') {
      oneMinuteWarningPlayed = false;
    }
  }, [session?.currentRound, session?.phase]);

  const handleTimeUp = async (currentSession: SessionState) => {
    try {
      if (currentSession.phase === 'play') {
        // Play phase ended, transition to buffer automatically
        playHorn('end');
        
        // Update session to buffer phase
        await fetch(`${EXPO_PUBLIC_BACKEND_URL}/api/session/horn`, { method: 'POST' });
        
        // Fetch updated session and matches
        await fetchSession();
        await fetchMatches();
        
      } else if (currentSession.phase === 'buffer') {
        // Buffer phase ended, start next round automatically
        playHorn('start');
        
        // Check if we should end the session or continue to next round
        const totalRounds = computeRoundsPlanned();
        
        if (currentSession.currentRound >= totalRounds) {
          // Session should end
          Alert.alert('🏆 Session Complete!', 'All planned rounds have been completed.', [{ text: 'OK' }]);
        } else {
          // Continue to next round
          await fetch(`${EXPO_PUBLIC_BACKEND_URL}/api/session/horn`, { method: 'POST' });
        }
        
        // Fetch updated session and matches
        await fetchSession();
        await fetchMatches();
      }
    } catch (error) {
      console.error('Error handling time up:', error);
    }
  };

  const initializeApp = async () => {
    try {
      setLoading(true);
      
      // Initialize backend data
      await fetch(`${EXPO_PUBLIC_BACKEND_URL}/api/init`, {
        method: 'POST',
      });

      // Fetch all data
      await Promise.all([
        fetchPlayers(),
        fetchCategories(), 
        fetchSession(),
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
      const response = await fetch(`${EXPO_PUBLIC_BACKEND_URL}/api/matches`);
      const data = await response.json();
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

  const computeRoundsPlanned = () => {
    if (!session) return 0;
    const totalSeconds = session.config.playSeconds + session.config.bufferSeconds;
    return Math.floor(7200 / Math.max(1, totalSeconds)); // 2 hours = 7200 seconds
  };

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

  // Start session function
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
        
        // Start the timer countdown immediately after session starts
        setTimeout(() => {
          startTimerCountdown();
        }, 500); // Small delay to ensure state is updated
      }
    } catch (error) {
      console.error('Error starting session:', error);
      Alert.alert('Error', 'Failed to start session');
    }
  };

  // CSV Import Function
  const importCSV = async () => {
    try {
      const result = await DocumentPicker.getDocumentAsync({
        type: 'text/csv',
        copyToCacheDirectory: true,
      });

      if (result.type === 'success') {
        const response = await fetch(result.uri);
        const csvText = await response.text();
        const importedPlayers = parseCSV(csvText);
        
        if (importedPlayers.length === 0) {
          Alert.alert('Error', 'No valid players found in CSV file');
          return;
        }

        // Show preview and confirm
        Alert.alert(
          'Import Players',
          `Found ${importedPlayers.length} players. Import them all?`,
          [
            { text: 'Cancel', style: 'cancel' },
            {
              text: 'Import',
              onPress: async () => {
                try {
                  for (const player of importedPlayers) {
                    await fetch(`${EXPO_PUBLIC_BACKEND_URL}/api/players`, {
                      method: 'POST',
                      headers: { 'Content-Type': 'application/json' },
                      body: JSON.stringify({
                        name: player.name,
                        category: player.category
                      })
                    });
                  }
                  await fetchPlayers();
                  Alert.alert('Success', `${importedPlayers.length} players imported successfully!`);
                } catch (error) {
                  Alert.alert('Error', 'Failed to import players');
                }
              }
            }
          ]
        );
      }
    } catch (error) {
      Alert.alert('Error', 'Failed to read CSV file');
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
      link.download = `pickleball-session-${new Date().toISOString().split('T')[0]}.csv`;
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
          <Text style={styles.loadingText}>Loading Pickleball Manager...</Text>
        </View>
      </SafeAreaView>
    );
  }

  return (
    <SafeAreaView style={styles.container}>
      <StatusBar barStyle="light-content" backgroundColor={colors.background} />
      
      {/* Header */}
      <View style={styles.header}>
        <Text style={styles.headerTitle}>Pickleball Session Manager</Text>
        {session && (
          <View style={styles.sessionInfo}>
            <Text style={styles.sessionText}>
              Round {session.currentRound}/{computeRoundsPlanned()} | {session.phase.toUpperCase()}
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
      </View>

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
            Players
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
              onStartSession={startSession}
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
  onStartSession
}: { 
  session: SessionState | null;
  categories: Category[];
  players: Player[];
  onRefresh: () => void;
  onImportCSV: () => void;
  onExportCSV: () => void;
  onStartSession: () => void;
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
    allowCrossCategory: false
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
        allowCrossCategory: session.config.allowCrossCategory || false
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
          allowCrossCategory: configForm.allowCrossCategory
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
              <Text style={styles.statValue}>{session.config.format.toUpperCase()}</Text>
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
          </View>
        )}

        {/* Single Session Control Button - Always "Let's Play" */}
        <View style={styles.sessionControlButtons}>
          <TouchableOpacity 
            style={[styles.primaryButton, players.length < 4 && styles.buttonDisabled]}
            onPress={onStartSession}
            disabled={players.length < 4}
          >
            <Ionicons name="play" size={20} color={colors.text} style={styles.buttonIcon} />
            <Text style={styles.buttonText}>Let's Play</Text>
          </TouchableOpacity>
        </View>
      </View>

      {/* CSV Import/Export */}
      <View style={styles.card}>
        <Text style={styles.cardTitle}>Data Management</Text>
        <Text style={styles.cardSubtitle}>
          Import/Export player data in CSV format
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
                    <View key={player.id} style={styles.playerItem}>
                      <Text style={styles.playerName}>{player.name}</Text>
                      <View style={styles.playerStats}>
                        <Text style={styles.playerStat}>W: {player.stats.wins}</Text>
                        <Text style={styles.playerStat}>L: {player.stats.losses}</Text>
                        <Text style={styles.playerStat}>Sits: {player.sitCount}</Text>
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
  onRefresh 
}: { 
  session: SessionState | null;
  matches: Match[];
  players: Player[];
  onRefresh: () => void;
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
      await fetch(`${EXPO_PUBLIC_BACKEND_URL}/api/matches/${match.id}/score`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ scoreA, scoreB })
      });

      // Clear score inputs for this match
      setScoreInputs(prev => {
        const newInputs = { ...prev };
        delete newInputs[match.id];
        return newInputs;
      });

      onRefresh();
      Alert.alert('Success', 'Score saved successfully!');
    } catch (error) {
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
  
  if (session.phase === 'idle') {
    return (
      <View style={styles.dashboardContainer}>
        <View style={styles.card}>
          <Ionicons name="tennisball" size={48} color={colors.success} />
          <Text style={styles.emptyTitle}>Session Not Started</Text>
          <Text style={styles.emptyText}>
            Start a session from the Admin tab to see court assignments
          </Text>
        </View>
      </View>
    );
  }

  const currentMatches = getCurrentMatches();
  const courts = Array.from({ length: session.config.numCourts }, (_, i) => i);
  
  return (
    <View style={styles.dashboardContainer}>
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

                {match.status === 'done' ? (
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
  const getCurrentAssignment = (playerId: string) => {
    // Find current round matches that include this player
    const currentRound = Math.max(0, ...matches.map(m => m.roundIndex));
    const currentMatches = matches.filter(m => m.roundIndex === currentRound);
    
    for (const match of currentMatches) {
      if ([...match.teamA, ...match.teamB].includes(playerId)) {
        return `Court ${match.courtIndex + 1} - ${match.matchType}`;
      }
    }
    
    return 'Sitting this round';
  };

  if (players.length === 0) {
    return (
      <View style={styles.dashboardContainer}>
        <View style={styles.card}>
          <Ionicons name="people" size={48} color={colors.primary} />
          <Text style={styles.emptyTitle}>No Players</Text>
          <Text style={styles.emptyText}>
            Add players from the Admin tab to get started
          </Text>
        </View>
      </View>
    );
  }

  return (
    <View style={styles.playersContainer}>
      {players.map((player) => (
        <View key={player.id} style={styles.playerCard}>
          <Text style={styles.playerCardName}>{player.name}</Text>
          <Text style={styles.playerCardCategory}>{player.category}</Text>
          <View style={styles.playerCardStats}>
            <Text style={styles.playerCardStat}>
              Record: {player.stats.wins}-{player.stats.losses}
            </Text>
            <Text style={styles.playerCardStat}>
              Point Diff: {player.stats.pointDiff > 0 ? '+' : ''}{player.stats.pointDiff}
            </Text>
            <Text style={styles.playerCardStat}>
              Sits: {player.sitCount}
            </Text>
          </View>
          <Text style={[
            styles.playerAssignment,
            getCurrentAssignment(player.id).includes('Court') ? styles.playerAssigned : null
          ]}>
            {getCurrentAssignment(player.id)}
          </Text>
        </View>
      ))}
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
    backgroundColor: colors.surface,
    padding: 20,
    borderBottomWidth: 1,
    borderBottomColor: colors.border,
  },
  headerTitle: {
    color: colors.text,
    fontSize: 24,
    fontWeight: '700',
    textAlign: 'center',
    letterSpacing: 0.5,
  },
  sessionInfo: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginTop: 12,
  },
  sessionText: {
    color: colors.textSecondary,
    fontSize: 16,
    fontWeight: '500',
  },
  timerText: {
    color: colors.success,
    fontSize: 20,
    fontWeight: '700',
    letterSpacing: 1,
  },
  timerWarning: {
    color: colors.warning,
  },
  timerIdle: {
    color: colors.textSecondary,
    opacity: 0.8,
  },
  tabContainer: {
    flexDirection: 'row',
    backgroundColor: colors.surface,
    borderBottomWidth: 1,
    borderBottomColor: colors.border,
  },
  tab: {
    flex: 1,
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    paddingVertical: 16,
    paddingHorizontal: 12,
  },
  activeTab: {
    backgroundColor: colors.primary,
  },
  tabText: {
    color: colors.textMuted,
    fontSize: 14,
    marginLeft: 6,
    fontWeight: '600',
  },
  activeTabText: {
    color: colors.text,
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
    backgroundColor: colors.surface,
    borderRadius: 16,
    padding: 20,
    marginBottom: 20,
    borderWidth: 1,
    borderColor: colors.border,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.1,
    shadowRadius: 8,
    elevation: 3,
  },
  cardTitle: {
    color: colors.text,
    fontSize: 20,
    fontWeight: '700',
    marginBottom: 8,
  },
  cardSubtitle: {
    color: colors.textSecondary,
    fontSize: 16,
    marginBottom: 16,
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
    fontSize: 16,
    fontWeight: '500',
    flex: 1,
  },
  configInput: {
    color: colors.text,
    fontSize: 16,
    padding: 12,
    backgroundColor: colors.surfaceLight,
    borderRadius: 8,
    borderWidth: 1,
    borderColor: colors.border,
    textAlign: 'center',
    minWidth: 70,
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
    paddingVertical: 10,
    paddingHorizontal: 16,
    borderRadius: 8,
    backgroundColor: colors.surfaceLight,
    borderWidth: 1,
    borderColor: colors.border,
  },
  toggleButtonActive: {
    backgroundColor: colors.success,
    borderColor: colors.success,
  },
  toggleButtonText: {
    color: colors.textSecondary,
    fontSize: 14,
    fontWeight: '500',
    textAlign: 'center',
  },
  toggleButtonTextActive: {
    color: colors.text,
    fontWeight: '600',
  },
  saveButton: {
    backgroundColor: colors.success,
    paddingVertical: 14,
    borderRadius: 10,
    alignItems: 'center',
    marginTop: 8,
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
    borderRadius: 10,
    alignItems: 'center',
    flexDirection: 'row',
    justifyContent: 'center',
    minWidth: 140,
  },
  warningButton: {
    flex: 1,
    backgroundColor: colors.warning,
    paddingVertical: 14,
    paddingHorizontal: 20,
    borderRadius: 10,
    alignItems: 'center',
    flexDirection: 'row',
    justifyContent: 'center',
    minWidth: 140,
  },
  dangerButton: {
    flex: 1,
    backgroundColor: colors.danger,
    paddingVertical: 14,
    paddingHorizontal: 20,
    borderRadius: 10,
    alignItems: 'center',
    flexDirection: 'row',
    justifyContent: 'center',
    minWidth: 140,
  },
  secondaryButton: {
    flex: 1,
    backgroundColor: 'transparent',
    paddingVertical: 14,
    paddingHorizontal: 20,
    borderRadius: 10,
    alignItems: 'center',
    flexDirection: 'row',
    justifyContent: 'center',
    borderWidth: 2,
    borderColor: colors.primary,
    minWidth: 140,
  },
  buttonDisabled: {
    backgroundColor: colors.surfaceLight,
    opacity: 0.6,
  },
  buttonIcon: {
    marginRight: 8,
  },
  buttonText: {
    color: colors.text,
    fontSize: 16,
    fontWeight: '600',
  },
  secondaryButtonText: {
    color: colors.primary,
    fontSize: 16,
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
    color: colors.text,
    fontSize: 16,
    padding: 16,
    minHeight: 50,
    backgroundColor: colors.surfaceLight,
    borderRadius: 10,
    borderWidth: 1,
    borderColor: colors.border,
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
    backgroundColor: colors.success,
    borderColor: colors.success,
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
});