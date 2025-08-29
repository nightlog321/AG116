import React, { useState, useEffect, useRef } from 'react';
import { View, Text, StyleSheet, ScrollView, TouchableOpacity, Alert, SafeAreaView, StatusBar, TextInput, KeyboardAvoidingView, Platform } from 'react-native';
import { Ionicons } from '@expo/vector-icons';

const EXPO_PUBLIC_BACKEND_URL = process.env.EXPO_PUBLIC_BACKEND_URL;

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
  format: 'singles' | 'doubles' | 'auto';
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

// Audio Context for horns
let audioContext: AudioContext | null = null;

const initializeAudio = () => {
  if (!audioContext) {
    audioContext = new (window.AudioContext || (window as any).webkitAudioContext)();
    if (audioContext.state === 'suspended') {
      audioContext.resume();
    }
  }
};

const playHorn = (type: 'start' | 'end' | 'manual') => {
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

  // Timer effect
  useEffect(() => {
    if (session && session.phase !== 'idle' && session.phase !== 'ended' && !session.paused && session.timeRemaining > 0) {
      timerRef.current = setInterval(() => {
        setSession(prev => {
          if (!prev || prev.timeRemaining <= 0) return prev;
          
          const newTimeRemaining = prev.timeRemaining - 1;
          
          if (newTimeRemaining <= 0) {
            // Time's up - trigger automatic phase transition
            handleTimeUp(prev);
          }
          
          return { ...prev, timeRemaining: newTimeRemaining };
        });
      }, 1000);
    } else if (timerRef.current) {
      clearInterval(timerRef.current);
      timerRef.current = null;
    }

    return () => {
      if (timerRef.current) {
        clearInterval(timerRef.current);
        timerRef.current = null;
      }
    };
  }, [session?.phase, session?.paused, session?.timeRemaining]);

  const handleTimeUp = async (currentSession: SessionState) => {
    try {
      if (currentSession.phase === 'play') {
        // Play phase ended, transition to buffer
        await fetch(`${EXPO_PUBLIC_BACKEND_URL}/api/session/horn`, { method: 'POST' });
        playHorn('end');
      } else if (currentSession.phase === 'buffer') {
        // Buffer phase ended, start next round or end session
        await fetch(`${EXPO_PUBLIC_BACKEND_URL}/api/session/horn`, { method: 'POST' });
        playHorn('start');
      }
      await fetchSession();
      await fetchMatches();
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

  if (loading) {
    return (
      <SafeAreaView style={styles.container}>
        <StatusBar barStyle="light-content" backgroundColor="#1a1a1a" />
        <View style={styles.loadingContainer}>
          <Text style={styles.loadingText}>Loading Pickleball Manager...</Text>
        </View>
      </SafeAreaView>
    );
  }

  return (
    <SafeAreaView style={styles.container}>
      <StatusBar barStyle="light-content" backgroundColor="#1a1a1a" />
      
      {/* Header */}
      <View style={styles.header}>
        <Text style={styles.headerTitle}>Pickleball Session Manager</Text>
        {session && (
          <View style={styles.sessionInfo}>
            <Text style={styles.sessionText}>
              Round {session.currentRound} | {session.phase.toUpperCase()}
              {session.paused && ' (PAUSED)'}
            </Text>
            {session.timeRemaining > 0 && session.phase !== 'idle' && (
              <Text style={[
                styles.timerText,
                session.timeRemaining <= 30 && session.phase === 'play' ? styles.timerWarning : null
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
            size={20} 
            color={activeTab === 'admin' ? '#ffffff' : '#666666'} 
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
            size={20} 
            color={activeTab === 'dashboard' ? '#ffffff' : '#666666'} 
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
            size={20} 
            color={activeTab === 'players' ? '#ffffff' : '#666666'} 
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
  onRefresh 
}: { 
  session: SessionState | null;
  categories: Category[];
  players: Player[];
  onRefresh: () => void;
}) {
  const [newPlayerName, setNewPlayerName] = useState('');
  const [selectedCategory, setSelectedCategory] = useState('');
  const [editingConfig, setEditingConfig] = useState(false);
  const [configForm, setConfigForm] = useState({
    numCourts: '6',
    playMinutes: '12',
    playSeconds: '00',
    bufferSeconds: '30',
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
          format: session.config.format,
          allowCrossCategory: configForm.allowCrossCategory
        })
      });

      setEditingConfig(false);
      onRefresh();
    } catch (error) {
      Alert.alert('Error', 'Failed to save configuration');
    }
  };

  const startSession = async () => {
    try {
      // Initialize audio on user interaction
      initializeAudio();
      
      const response = await fetch(`${EXPO_PUBLIC_BACKEND_URL}/api/session/start`, {
        method: 'POST'
      });
      
      if (response.ok) {
        playHorn('start');
        onRefresh();
      }
    } catch (error) {
      Alert.alert('Error', 'Failed to start session');
    }
  };

  const startPlay = async () => {
    try {
      initializeAudio();
      
      const response = await fetch(`${EXPO_PUBLIC_BACKEND_URL}/api/session/play`, {
        method: 'POST'
      });
      
      if (response.ok) {
        playHorn('start');
        onRefresh();
      }
    } catch (error) {
      Alert.alert('Error', 'Failed to start play');
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

  const resetSession = async () => {
    Alert.alert(
      'Reset Session',
      'This will clear all matches and reset player stats. Continue?',
      [
        { text: 'Cancel', style: 'cancel' },
        {
          text: 'Reset',
          style: 'destructive',
          onPress: async () => {
            try {
              await fetch(`${EXPO_PUBLIC_BACKEND_URL}/api/session/reset`, {
                method: 'POST'
              });
              onRefresh();
            } catch (error) {
              Alert.alert('Error', 'Failed to reset session');
            }
          }
        }
      ]
    );
  };

  if (!session) return <Text style={styles.loadingText}>Loading session...</Text>;

  return (
    <View style={styles.adminContainer}>
      {/* Session Controls */}
      <View style={styles.card}>
        <View style={styles.cardHeader}>
          <Text style={styles.cardTitle}>Session Configuration</Text>
          <TouchableOpacity 
            style={styles.editButton}
            onPress={() => {
              if (session.phase !== 'idle' && !editingConfig) {
                Alert.alert(
                  'Edit Configuration',
                  'Editing configuration during an active session may affect ongoing matches. Continue?',
                  [
                    { text: 'Cancel', style: 'cancel' },
                    { text: 'Edit Anyway', onPress: () => setEditingConfig(true) }
                  ]
                );
              } else {
                setEditingConfig(!editingConfig);
              }
            }}
          >
            <Ionicons 
              name={editingConfig ? "checkmark" : "pencil"} 
              size={20} 
              color="#4CAF50"
            />
          </TouchableOpacity>
        </View>
        
        {editingConfig && session.phase === 'idle' ? (
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
                />
                <Text style={styles.timeColon}>:</Text>
                <TextInput
                  style={styles.timeInput}
                  value={configForm.playSeconds}
                  onChangeText={(text) => setConfigForm({...configForm, playSeconds: text})}
                  keyboardType="numeric"
                  maxLength={2}
                  placeholder="00"
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

        <View style={styles.buttonRow}>
          {session.phase === 'idle' ? (
            <TouchableOpacity 
              style={[styles.button, players.length < 4 && styles.buttonDisabled]}
              onPress={startSession}
              disabled={players.length < 4}
            >
              <Ionicons name="play" size={20} color="#ffffff" style={styles.buttonIcon} />
              <Text style={styles.buttonText}>Let's Play!</Text>
            </TouchableOpacity>
          ) : (
            <>
              {session.phase === 'play' || session.phase === 'buffer' ? (
                <TouchableOpacity 
                  style={[styles.button, styles.pauseButton]}
                  onPress={pauseResume}
                >
                  <Ionicons 
                    name={session.paused ? "play" : "pause"} 
                    size={20} 
                    color="#ffffff" 
                    style={styles.buttonIcon}
                  />
                  <Text style={styles.buttonText}>
                    {session.paused ? 'Resume' : 'Pause'}
                  </Text>
                </TouchableOpacity>
              ) : null}
              
              <TouchableOpacity 
                style={[styles.button, styles.hornButton]}
                onPress={manualHorn}
              >
                <Ionicons name="megaphone" size={20} color="#ffffff" style={styles.buttonIcon} />
                <Text style={styles.buttonText}>Horn Now</Text>
              </TouchableOpacity>
            </>
          )}
          
          <TouchableOpacity 
            style={[styles.button, styles.secondaryButton]}
            onPress={resetSession}
          >
            <Text style={[styles.buttonText, styles.secondaryButtonText]}>Reset</Text>
          </TouchableOpacity>
        </View>
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
            placeholderTextColor="#666666"
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
          style={[styles.button, !newPlayerName.trim() && styles.buttonDisabled]}
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

// Courts Dashboard Component  
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
          <Ionicons name="tennisball" size={48} color="#4CAF50" />
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
                    color="#4CAF50" 
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
                        placeholderTextColor="#666666"
                        maxLength={2}
                      />
                      
                      <Text style={styles.scoreLabel}>Team B:</Text>
                      <TextInput
                        style={styles.scoreInputField}
                        value={scoreInputs[match.id]?.scoreB || ''}
                        onChangeText={(text) => updateScoreInput(match.id, 'B', text)}
                        keyboardType="numeric"
                        placeholder="0"
                        placeholderTextColor="#666666"
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
                <Ionicons name="tennisball-outline" size={32} color="#666666" />
                <Text style={styles.emptyCourtText}>No match assigned</Text>
              </View>
            )}
          </View>
        );
      })}
    </View>
  );
}

// Players Board Component
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
          <Ionicons name="people" size={48} color="#2196F3" />
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
    backgroundColor: '#1a1a1a',
  },
  loadingContainer: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
  },
  loadingText: {
    color: '#ffffff',
    fontSize: 16,
    textAlign: 'center',
  },
  header: {
    backgroundColor: '#2c2c2c',
    padding: 16,
    borderBottomWidth: 1,
    borderBottomColor: '#333333',
  },
  headerTitle: {
    color: '#ffffff',
    fontSize: 20,
    fontWeight: 'bold',
    textAlign: 'center',
  },
  sessionInfo: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginTop: 8,
  },
  sessionText: {
    color: '#cccccc',
    fontSize: 14,
  },
  timerText: {
    color: '#4CAF50',
    fontSize: 16,
    fontWeight: 'bold',
  },
  timerWarning: {
    color: '#FF5722',
  },
  tabContainer: {
    flexDirection: 'row',
    backgroundColor: '#2c2c2c',
    borderBottomWidth: 1,
    borderBottomColor: '#333333',
  },
  tab: {
    flex: 1,
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    paddingVertical: 12,
    paddingHorizontal: 8,
  },
  activeTab: {
    backgroundColor: '#4CAF50',
  },
  tabText: {
    color: '#666666',
    fontSize: 12,
    marginLeft: 4,
    fontWeight: '500',
  },
  activeTabText: {
    color: '#ffffff',
  },
  content: {
    flex: 1,
  },
  keyboardContainer: {
    flex: 1,
  },
  adminContainer: {
    padding: 16,
  },
  card: {
    backgroundColor: '#2c2c2c',
    borderRadius: 12,
    padding: 16,
    marginBottom: 16,
    borderWidth: 1,
    borderColor: '#333333',
  },
  cardTitle: {
    color: '#ffffff',
    fontSize: 18,
    fontWeight: 'bold',
    marginBottom: 16,
  },
  cardHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: 16,
  },
  editButton: {
    padding: 8,
    borderRadius: 20,
    backgroundColor: '#333333',
  },
  configForm: {
    gap: 16,
  },
  configRow: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
  },
  configLabel: {
    color: '#cccccc',
    fontSize: 16,
    flex: 1,
  },
  configInput: {
    color: '#ffffff',
    fontSize: 16,
    padding: 8,
    backgroundColor: '#333333',
    borderRadius: 6,
    borderWidth: 1,
    borderColor: '#444444',
    textAlign: 'center',
    minWidth: 60,
  },
  timeInputs: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 4,
  },
  timeInput: {
    color: '#ffffff',
    fontSize: 16,
    padding: 8,
    backgroundColor: '#333333',
    borderRadius: 6,
    borderWidth: 1,
    borderColor: '#444444',
    textAlign: 'center',
    width: 40,
  },
  timeColon: {
    color: '#ffffff',
    fontSize: 16,
    fontWeight: 'bold',
  },
  toggleButton: {
    paddingVertical: 8,
    paddingHorizontal: 16,
    borderRadius: 6,
    backgroundColor: '#333333',
    borderWidth: 1,
    borderColor: '#444444',
  },
  toggleButtonActive: {
    backgroundColor: '#4CAF50',
    borderColor: '#4CAF50',
  },
  toggleButtonText: {
    color: '#cccccc',
    fontSize: 14,
    textAlign: 'center',
  },
  toggleButtonTextActive: {
    color: '#ffffff',
    fontWeight: 'bold',
  },
  saveButton: {
    backgroundColor: '#4CAF50',
    paddingVertical: 12,
    borderRadius: 8,
    alignItems: 'center',
    marginTop: 8,
  },
  saveButtonText: {
    color: '#ffffff',
    fontSize: 16,
    fontWeight: 'bold',
  },
  sessionStats: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    justifyContent: 'space-between',
    marginBottom: 16,
  },
  statItem: {
    alignItems: 'center',
    minWidth: '30%',
    marginBottom: 8,
  },
  statLabel: {
    color: '#cccccc',
    fontSize: 12,
    marginBottom: 4,
  },
  statValue: {
    color: '#ffffff',
    fontSize: 16,
    fontWeight: 'bold',
  },
  buttonRow: {
    flexDirection: 'row',
    gap: 12,
    flexWrap: 'wrap',
  },
  button: {
    flex: 1,
    backgroundColor: '#4CAF50',
    paddingVertical: 12,
    paddingHorizontal: 16,
    borderRadius: 8,
    alignItems: 'center',
    flexDirection: 'row',
    justifyContent: 'center',
    minWidth: 120,
  },
  buttonDisabled: {
    backgroundColor: '#333333',
  },
  buttonIcon: {
    marginRight: 8,
  },
  buttonText: {
    color: '#ffffff',
    fontSize: 16,
    fontWeight: 'bold',
  },
  pauseButton: {
    backgroundColor: '#FF9800',
  },
  hornButton: {
    backgroundColor: '#F44336',
  },
  secondaryButton: {
    backgroundColor: 'transparent',
    borderWidth: 1,
    borderColor: '#666666',
  },
  secondaryButtonText: {
    color: '#cccccc',
  },
  inputGroup: {
    marginBottom: 16,
  },
  inputLabel: {
    color: '#cccccc',
    fontSize: 14,
    marginBottom: 8,
  },
  textInput: {
    color: '#ffffff',
    fontSize: 16,
    padding: 12,
    minHeight: 44,
    backgroundColor: '#333333',
    borderRadius: 8,
    borderWidth: 1,
    borderColor: '#444444',
  },
  categoryButtons: {
    flexDirection: 'row',
    gap: 8,
  },
  categoryButton: {
    flex: 1,
    paddingVertical: 8,
    paddingHorizontal: 12,
    borderRadius: 8,
    backgroundColor: '#333333',
    borderWidth: 1,
    borderColor: '#444444',
    alignItems: 'center',
  },
  categoryButtonActive: {
    backgroundColor: '#4CAF50',
    borderColor: '#4CAF50',
  },
  categoryButtonText: {
    color: '#cccccc',
    fontSize: 14,
  },
  categoryButtonTextActive: {
    color: '#ffffff',
    fontWeight: 'bold',
  },
  emptyText: {
    color: '#666666',
    fontSize: 14,
    textAlign: 'center',
    fontStyle: 'italic',
  },
  playersList: {
    gap: 12,
  },
  categorySection: {
    marginBottom: 16,
  },
  categoryHeader: {
    color: '#4CAF50',
    fontSize: 14,
    fontWeight: 'bold',
    marginBottom: 8,
  },
  playerItem: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    paddingVertical: 8,
    paddingHorizontal: 12,
    backgroundColor: '#333333',
    borderRadius: 8,
    marginBottom: 4,
  },
  playerName: {
    color: '#ffffff',
    fontSize: 16,
    flex: 1,
  },
  playerStats: {
    flexDirection: 'row',
    gap: 12,
  },
  playerStat: {
    color: '#cccccc',
    fontSize: 12,
  },
  dashboardContainer: {
    padding: 16,
  },
  emptyTitle: {
    color: '#ffffff',
    fontSize: 20,
    fontWeight: 'bold',
    textAlign: 'center',
    marginTop: 16,
    marginBottom: 8,
  },
  courtCard: {
    backgroundColor: '#2c2c2c',
    borderRadius: 12,
    padding: 16,
    marginBottom: 12,
    borderWidth: 1,
    borderColor: '#333333',
  },
  courtHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: 12,
  },
  courtTitle: {
    color: '#ffffff',
    fontSize: 18,
    fontWeight: 'bold',
  },
  matchBadge: {
    backgroundColor: '#4CAF50',
    paddingHorizontal: 8,
    paddingVertical: 4,
    borderRadius: 12,
  },
  matchBadgeText: {
    color: '#ffffff',
    fontSize: 12,
    fontWeight: 'bold',
  },
  matchDetails: {
    gap: 12,
  },
  matchType: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 8,
  },
  matchTypeText: {
    color: '#4CAF50',
    fontSize: 14,
    fontWeight: '500',
  },
  teamsContainer: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-around',
    backgroundColor: '#333333',
    borderRadius: 8,
    padding: 12,
  },
  team: {
    alignItems: 'center',
    flex: 1,
  },
  teamLabel: {
    color: '#cccccc',
    fontSize: 12,
    marginBottom: 4,
    fontWeight: 'bold',
  },
  playerNameInMatch: {
    color: '#ffffff',
    fontSize: 14,
    marginBottom: 2,
  },
  vsText: {
    color: '#4CAF50',
    fontSize: 16,
    fontWeight: 'bold',
    marginHorizontal: 16,
  },
  scoreInput: {
    backgroundColor: '#333333',
    borderRadius: 8,
    padding: 12,
  },
  scoreInputRow: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    marginBottom: 12,
  },
  scoreLabel: {
    color: '#cccccc',
    fontSize: 14,
  },
  scoreInputField: {
    backgroundColor: '#2c2c2c',
    borderWidth: 1,
    borderColor: '#444444',
    borderRadius: 6,
    paddingHorizontal: 12,
    paddingVertical: 8,
    color: '#ffffff',
    fontSize: 16,
    textAlign: 'center',
    minWidth: 60,
  },
  saveScoreButton: {
    backgroundColor: '#4CAF50',
    paddingVertical: 10,
    borderRadius: 6,
    alignItems: 'center',
  },
  saveScoreButtonText: {
    color: '#ffffff',
    fontSize: 14,
    fontWeight: 'bold',
  },
  finalScore: {
    backgroundColor: '#333333',
    borderRadius: 8,
    padding: 12,
    alignItems: 'center',
  },
  finalScoreText: {
    color: '#4CAF50',
    fontSize: 16,
    fontWeight: 'bold',
  },
  matchStatus: {
    alignItems: 'center',
  },
  matchStatusText: {
    color: '#cccccc',
    fontSize: 12,
    fontStyle: 'italic',
  },
  emptyCourt: {
    alignItems: 'center',
    paddingVertical: 24,
  },
  emptyCourtText: {
    color: '#666666',
    fontSize: 14,
    marginTop: 8,
  },
  playersContainer: {
    padding: 16,
  },
  playerCard: {
    backgroundColor: '#2c2c2c',
    borderRadius: 12,
    padding: 16,
    marginBottom: 12,
    borderWidth: 1,
    borderColor: '#333333',
  },
  playerCardName: {
    color: '#ffffff',
    fontSize: 18,
    fontWeight: 'bold',
    marginBottom: 4,
  },
  playerCardCategory: {
    color: '#4CAF50',
    fontSize: 14,
    marginBottom: 12,
  },
  playerCardStats: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    marginBottom: 8,
  },
  playerCardStat: {
    color: '#cccccc',
    fontSize: 12,
  },
  playerAssignment: {
    color: '#666666',
    fontSize: 14,
    fontStyle: 'italic',
    textAlign: 'center',
    marginTop: 8,
  },
  playerAssigned: {
    color: '#4CAF50',
    fontWeight: 'bold',
  },
});