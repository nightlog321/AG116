import React, { useState, useEffect } from 'react';
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

interface SessionConfig {
  numCourts: number;
  playSeconds: number;
  bufferSeconds: number;
  format: 'singles' | 'doubles' | 'auto';
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

export default function PickleballManager() {
  const [activeTab, setActiveTab] = useState('admin');
  const [players, setPlayers] = useState<Player[]>([]);
  const [categories, setCategories] = useState<Category[]>([]);
  const [session, setSession] = useState<SessionState | null>(null);
  const [loading, setLoading] = useState(true);

  // Initialize data
  useEffect(() => {
    initializeApp();
  }, []);

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
        fetchSession()
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
            </Text>
            {session.timeRemaining > 0 && (
              <Text style={styles.timerText}>
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
            <CourtsDashboard session={session} />
          )}
          
          {activeTab === 'players' && (
            <PlayersBoard players={players} />
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
    bufferSeconds: '30'
  });

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
        bufferSeconds: session.config.bufferSeconds.toString()
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
          format: session.config.format
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
      await fetch(`${EXPO_PUBLIC_BACKEND_URL}/api/session/start`, {
        method: 'POST'
      });
      onRefresh();
    } catch (error) {
      Alert.alert('Error', 'Failed to start session');
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
        <Text style={styles.cardTitle}>Session Controls</Text>
        
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
        </View>

        <View style={styles.buttonRow}>
          {session.phase === 'idle' ? (
            <TouchableOpacity 
              style={[styles.button, players.length < 4 && styles.buttonDisabled]}
              onPress={startSession}
              disabled={players.length < 4}
            >
              <Text style={styles.buttonText}>Start Session</Text>
            </TouchableOpacity>
          ) : (
            <TouchableOpacity style={styles.button}>
              <Text style={styles.buttonText}>Horn Now</Text>
            </TouchableOpacity>
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
function CourtsDashboard({ session }: { session: SessionState | null }) {
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

  // Placeholder for when we implement match display
  const courts = Array.from({ length: session.config.numCourts }, (_, i) => i);
  
  return (
    <View style={styles.dashboardContainer}>
      {courts.map((courtIndex) => (
        <View key={courtIndex} style={styles.courtCard}>
          <View style={styles.courtHeader}>
            <Text style={styles.courtTitle}>Court {courtIndex + 1}</Text>
            <Text style={styles.courtStatus}>Available</Text>
          </View>
          <Text style={styles.emptyText}>No match assigned</Text>
        </View>
      ))}
    </View>
  );
}

// Players Board Component
function PlayersBoard({ players }: { players: Player[] }) {
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
          <Text style={styles.playerAssignment}>
            {/* This will show current assignment when implemented */}
            Waiting for assignment
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
  sessionStats: {
    flexDirection: 'row',
    justifyContent: 'space-around',
    marginBottom: 16,
  },
  statItem: {
    alignItems: 'center',
  },
  statLabel: {
    color: '#cccccc',
    fontSize: 12,
    marginBottom: 4,
  },
  statValue: {
    color: '#ffffff',
    fontSize: 20,
    fontWeight: 'bold',
  },
  buttonRow: {
    flexDirection: 'row',
    gap: 12,
  },
  button: {
    flex: 1,
    backgroundColor: '#4CAF50',
    paddingVertical: 12,
    borderRadius: 8,
    alignItems: 'center',
  },
  buttonDisabled: {
    backgroundColor: '#333333',
  },
  buttonText: {
    color: '#ffffff',
    fontSize: 16,
    fontWeight: 'bold',
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
  inputContainer: {
    backgroundColor: '#333333',
    borderRadius: 8,
    borderWidth: 1,
    borderColor: '#444444',
  },
  input: {
    color: '#ffffff',
    fontSize: 16,
    padding: 12,
    minHeight: 44,
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
  courtStatus: {
    color: '#4CAF50',
    fontSize: 14,
    fontWeight: '500',
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
});