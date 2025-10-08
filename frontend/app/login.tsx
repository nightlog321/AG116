import React, { useState } from 'react';
import { View, Text, TextInput, TouchableOpacity, Alert, SafeAreaView, StatusBar, KeyboardAvoidingView, Platform } from 'react-native';
import { LinearGradient } from 'expo-linear-gradient';
import { Ionicons } from '@expo/vector-icons';
import { router } from 'expo-router';
import AsyncStorage from '@react-native-async-storage/async-storage';

const EXPO_PUBLIC_BACKEND_URL = process.env.EXPO_PUBLIC_BACKEND_URL;

// Color palette
const colors = {
  background: '#ffffff',
  surface: '#f8fafc',
  primary: '#3b82f6',
  primaryDark: '#2563eb',
  primaryGradient: ['#3b82f6', '#06b6d4'],
  text: '#1e293b',
  textSecondary: '#64748b',
  textMuted: '#94a3b8',
  border: '#e2e8f0',
  success: '#10b981',
  error: '#ef4444',
};

const styles = {
  container: {
    flex: 1,
    backgroundColor: colors.background,
  },
  content: {
    flex: 1,
    padding: 24,
    justifyContent: 'center',
  },
  logoContainer: {
    alignItems: 'center',
    marginBottom: 48,
  },
  logo: {
    fontSize: 32,
    fontWeight: 'bold',
    color: colors.primary,
    marginBottom: 8,
  },
  subtitle: {
    fontSize: 16,
    color: colors.textSecondary,
    textAlign: 'center',
  },
  formContainer: {
    marginBottom: 24,
  },
  inputGroup: {
    marginBottom: 20,
  },
  inputLabel: {
    fontSize: 16,
    fontWeight: '600',
    color: colors.text,
    marginBottom: 8,
  },
  textInput: {
    borderWidth: 1,
    borderColor: colors.border,
    borderRadius: 12,
    padding: 16,
    fontSize: 16,
    backgroundColor: colors.surface,
    color: colors.text,
  },
  buttonContainer: {
    marginBottom: 24,
  },
  primaryButton: {
    borderRadius: 12,
    paddingVertical: 16,
    paddingHorizontal: 24,
    marginBottom: 12,
  },
  buttonText: {
    fontSize: 16,
    fontWeight: '600',
    color: '#ffffff',
    textAlign: 'center',
  },
  secondaryButton: {
    borderWidth: 1,
    borderColor: colors.primary,
    borderRadius: 12,
    paddingVertical: 16,
    paddingHorizontal: 24,
  },
  secondaryButtonText: {
    fontSize: 16,
    fontWeight: '600',
    color: colors.primary,
    textAlign: 'center',
  },
  switchModeText: {
    fontSize: 14,
    color: colors.textSecondary,
    textAlign: 'center',
    marginTop: 16,
  },
  switchModeLink: {
    color: colors.primary,
    fontWeight: '600',
  },
  demoSection: {
    backgroundColor: colors.surface,
    borderRadius: 12,
    padding: 16,
    marginTop: 24,
  },
  demoTitle: {
    fontSize: 16,
    fontWeight: '600',
    color: colors.text,
    marginBottom: 8,
  },
  demoText: {
    fontSize: 14,
    color: colors.textSecondary,
    lineHeight: 20,
  },
};

export default function LoginScreen() {
  const [mode, setMode] = useState<'login' | 'register'>('login');
  const [clubName, setClubName] = useState('');
  const [accessCode, setAccessCode] = useState('');
  const [displayName, setDisplayName] = useState('');
  const [description, setDescription] = useState('');
  const [loading, setLoading] = useState(false);

  const handleLogin = async () => {
    if (!clubName.trim() || !accessCode.trim()) {
      Alert.alert('Error', 'Please enter both club name and access code');
      return;
    }

    setLoading(true);
    try {
      const response = await fetch(`${EXPO_PUBLIC_BACKEND_URL}/api/auth/login`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          club_name: clubName.trim(),
          access_code: accessCode.trim(),
        }),
      });

      const data = await response.json();

      if (response.ok) {
        // Store club session
        await AsyncStorage.setItem('clubSession', JSON.stringify(data));
        
        // Add a small delay to ensure storage is written
        await new Promise(resolve => setTimeout(resolve, 500));
        
        // Redirect to main app
        router.replace('/');
      } else {
        Alert.alert('Login Failed', data.detail || 'Invalid club name or access code');
      }
    } catch (error) {
      Alert.alert('Error', 'Failed to connect to server. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  const handleRegister = async () => {
    if (!clubName.trim() || !displayName.trim() || !accessCode.trim()) {
      Alert.alert('Error', 'Please fill in all required fields');
      return;
    }

    setLoading(true);
    try {
      const response = await fetch(`${EXPO_PUBLIC_BACKEND_URL}/api/auth/register`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          name: clubName.trim(),
          display_name: displayName.trim(),
          access_code: accessCode.trim(),
          description: description.trim() || null,
        }),
      });

      const data = await response.json();

      if (response.ok) {
        // Store club session
        await AsyncStorage.setItem('clubSession', JSON.stringify(data));
        
        // Add a small delay to ensure storage is written
        await new Promise(resolve => setTimeout(resolve, 500));
        
        // Redirect to main app
        router.replace('/');
      } else {
        Alert.alert('Registration Failed', data.detail || 'Failed to create club');
      }
    } catch (error) {
      Alert.alert('Error', 'Failed to connect to server. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  const tryDemo = async () => {
    setClubName('Main Club');
    setAccessCode('demo123');
    setTimeout(() => handleLogin(), 100);
  };

  return (
    <SafeAreaView style={styles.container}>
      <StatusBar barStyle="dark-content" backgroundColor={colors.background} />
      
      <KeyboardAvoidingView 
        style={{ flex: 1 }}
        behavior={Platform.OS === 'ios' ? 'padding' : 'height'}
      >
        <View style={styles.content}>
          
          {/* Logo and Title */}
          <View style={styles.logoContainer}>
            <Text style={styles.logo}>🏓 CourtChime</Text>
            <Text style={styles.subtitle}>
              {mode === 'login' ? 'Sign into your club' : 'Create a new club'}
            </Text>
          </View>

          {/* Form */}
          <View style={styles.formContainer}>
            <View style={styles.inputGroup}>
              <Text style={styles.inputLabel}>Club Name</Text>
              <TextInput
                style={styles.textInput}
                value={clubName}
                onChangeText={setClubName}
                placeholder="Enter your club name"
                placeholderTextColor={colors.textMuted}
                autoCapitalize="words"
                autoCorrect={false}
              />
            </View>

            {mode === 'register' && (
              <View style={styles.inputGroup}>
                <Text style={styles.inputLabel}>Display Name</Text>
                <TextInput
                  style={styles.textInput}
                  value={displayName}
                  onChangeText={setDisplayName}
                  placeholder="How your club appears to members"
                  placeholderTextColor={colors.textMuted}
                  autoCapitalize="words"
                />
              </View>
            )}

            <View style={styles.inputGroup}>
              <Text style={styles.inputLabel}>Access Code</Text>
              <TextInput
                style={styles.textInput}
                value={accessCode}
                onChangeText={setAccessCode}
                placeholder={mode === 'login' ? 'Enter access code' : 'Create access code'}
                placeholderTextColor={colors.textMuted}
                autoCapitalize="none"
                autoCorrect={false}
                secureTextEntry={false}
              />
            </View>

            {mode === 'register' && (
              <View style={styles.inputGroup}>
                <Text style={styles.inputLabel}>Description (Optional)</Text>
                <TextInput
                  style={styles.textInput}
                  value={description}
                  onChangeText={setDescription}
                  placeholder="Brief description of your club"
                  placeholderTextColor={colors.textMuted}
                  multiline
                />
              </View>
            )}
          </View>

          {/* Action Buttons */}
          <View style={styles.buttonContainer}>
            <TouchableOpacity 
              onPress={mode === 'login' ? handleLogin : handleRegister}
              disabled={loading}
            >
              <LinearGradient
                colors={colors.primaryGradient}
                start={{ x: 0, y: 0 }}
                end={{ x: 1, y: 0 }}
                style={styles.primaryButton}
              >
                <Text style={styles.buttonText}>
                  {loading ? 'Processing...' : (mode === 'login' ? 'Sign In' : 'Create Club')}
                </Text>
              </LinearGradient>
            </TouchableOpacity>

            <TouchableOpacity 
              style={styles.secondaryButton}
              onPress={() => setMode(mode === 'login' ? 'register' : 'login')}
            >
              <Text style={styles.secondaryButtonText}>
                {mode === 'login' ? 'Create New Club' : 'Sign Into Existing Club'}
              </Text>
            </TouchableOpacity>
          </View>

          {/* Mode Switch Text */}
          <Text style={styles.switchModeText}>
            {mode === 'login' 
              ? "Don't have a club? " 
              : "Already have a club? "
            }
            <Text 
              style={styles.switchModeLink}
              onPress={() => setMode(mode === 'login' ? 'register' : 'login')}
            >
              {mode === 'login' ? 'Create one' : 'Sign in'}
            </Text>
          </Text>

          {/* Demo Section */}
          {mode === 'login' && (
            <View style={styles.demoSection}>
              <Text style={styles.demoTitle}>
                <Ionicons name="flask" size={16} color={colors.primary} /> Try Demo
              </Text>
              <Text style={styles.demoText}>
                Club: "Main Club" | Access Code: "demo123"
              </Text>
              <TouchableOpacity 
                onPress={tryDemo}
                style={{ marginTop: 12 }}
              >
                <Text style={styles.switchModeLink}>Quick Demo Access →</Text>
              </TouchableOpacity>
            </View>
          )}

        </View>
      </KeyboardAvoidingView>
    </SafeAreaView>
  );
}