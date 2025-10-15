import React, { useState } from 'react';
import { View, Text, TextInput, TouchableOpacity, Alert, SafeAreaView, StatusBar, KeyboardAvoidingView, Platform } from 'react-native';
import { LinearGradient } from 'expo-linear-gradient';
import { Ionicons } from '@expo/vector-icons';
import { router } from 'expo-router';
import AsyncStorage from '@react-native-async-storage/async-storage';

const EXPO_PUBLIC_BACKEND_URL = process.env.EXPO_PUBLIC_BACKEND_URL;

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
        await AsyncStorage.setItem('clubSession', JSON.stringify(data));
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
        await AsyncStorage.setItem('clubSession', JSON.stringify(data));
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
    <SafeAreaView style={{flex: 1, backgroundColor: '#ffffff'}}>
      <StatusBar barStyle="dark-content" backgroundColor="#ffffff" />
      <KeyboardAvoidingView 
        style={{ flex: 1 }}
        behavior={Platform.OS === 'ios' ? 'padding' : 'height'}
      >
        <View style={{flex: 1, padding: 24, justifyContent: 'center'}}>
          <View style={{alignItems: 'center', marginBottom: 48}}>
            <Text style={{fontSize: 32, fontWeight: 'bold', color: '#3b82f6', marginBottom: 8}}>
              🏓 CourtChime
            </Text>
            <Text style={{fontSize: 16, color: '#64748b', textAlign: 'center'}}>
              {mode === 'login' ? 'Sign into your club' : 'Create a new club'}
            </Text>
          </View>

          <View style={{marginBottom: 24}}>
            <View style={{marginBottom: 20}}>
              <Text style={{fontSize: 16, fontWeight: '600', color: '#1e293b', marginBottom: 8}}>
                Club Name
              </Text>
              <TextInput
                style={{
                  borderWidth: 1, borderColor: '#e2e8f0', borderRadius: 12, padding: 16,
                  fontSize: 16, backgroundColor: '#f8fafc', color: '#1e293b'
                }}
                value={clubName}
                onChangeText={setClubName}
                placeholder="Enter your club name"
                placeholderTextColor="#94a3b8"
                autoCapitalize="words"
                autoCorrect={false}
              />
            </View>

            {mode === 'register' && (
              <View style={{marginBottom: 20}}>
                <Text style={{fontSize: 16, fontWeight: '600', color: '#1e293b', marginBottom: 8}}>
                  Display Name
                </Text>
                <TextInput
                  style={{
                    borderWidth: 1, borderColor: '#e2e8f0', borderRadius: 12, padding: 16,
                    fontSize: 16, backgroundColor: '#f8fafc', color: '#1e293b'
                  }}
                  value={displayName}
                  onChangeText={setDisplayName}
                  placeholder="How your club appears to members"
                  placeholderTextColor="#94a3b8"
                  autoCapitalize="words"
                />
              </View>
            )}

            <View style={{marginBottom: 20}}>
              <Text style={{fontSize: 16, fontWeight: '600', color: '#1e293b', marginBottom: 8}}>
                Access Code
              </Text>
              <TextInput
                style={{
                  borderWidth: 1, borderColor: '#e2e8f0', borderRadius: 12, padding: 16,
                  fontSize: 16, backgroundColor: '#f8fafc', color: '#1e293b'
                }}
                value={accessCode}
                onChangeText={setAccessCode}
                placeholder={mode === 'login' ? 'Enter access code' : 'Create access code'}
                placeholderTextColor="#94a3b8"
                autoCapitalize="none"
                autoCorrect={false}
              />
            </View>

            {mode === 'register' && (
              <View style={{marginBottom: 20}}>
                <Text style={{fontSize: 16, fontWeight: '600', color: '#1e293b', marginBottom: 8}}>
                  Description (Optional)
                </Text>
                <TextInput
                  style={{
                    borderWidth: 1, borderColor: '#e2e8f0', borderRadius: 12, padding: 16,
                    fontSize: 16, backgroundColor: '#f8fafc', color: '#1e293b'
                  }}
                  value={description}
                  onChangeText={setDescription}
                  placeholder="Brief description of your club"
                  placeholderTextColor="#94a3b8"
                  multiline
                />
              </View>
            )}
          </View>

          <View style={{marginBottom: 24}}>
            <TouchableOpacity 
              onPress={mode === 'login' ? handleLogin : handleRegister}
              disabled={loading}
            >
              <LinearGradient
                colors={['#3b82f6', '#06b6d4']}
                start={{ x: 0, y: 0 }}
                end={{ x: 1, y: 0 }}
                style={{
                  borderRadius: 12, paddingVertical: 16, paddingHorizontal: 24, marginBottom: 12
                }}
              >
                <Text style={{
                  fontSize: 16, fontWeight: '600', color: '#ffffff', textAlign: 'center'
                }}>
                  {loading ? 'Processing...' : (mode === 'login' ? 'Sign In' : 'Create Club')}
                </Text>
              </LinearGradient>
            </TouchableOpacity>

            <TouchableOpacity 
              style={{
                borderWidth: 1, borderColor: '#3b82f6', borderRadius: 12,
                paddingVertical: 16, paddingHorizontal: 24
              }}
              onPress={() => setMode(mode === 'login' ? 'register' : 'login')}
            >
              <Text style={{
                fontSize: 16, fontWeight: '600', color: '#3b82f6', textAlign: 'center'
              }}>
                {mode === 'login' ? 'Create New Club' : 'Sign Into Existing Club'}
              </Text>
            </TouchableOpacity>
          </View>

          {mode === 'login' && (
            <View style={{
              backgroundColor: '#f8fafc', borderRadius: 12, padding: 16, marginTop: 24
            }}>
              <Text style={{
                fontSize: 16, fontWeight: '600', color: '#1e293b', marginBottom: 8
              }}>
                <Ionicons name="flask" size={16} color="#3b82f6" /> Try Demo
              </Text>
              <Text style={{
                fontSize: 14, color: '#64748b', lineHeight: 20
              }}>
                Club: "Main Club" | Access Code: "demo123"
              </Text>
              <TouchableOpacity onPress={tryDemo} style={{ marginTop: 12 }}>
                <Text style={{color: '#3b82f6', fontWeight: '600'}}>Quick Demo Access →</Text>
              </TouchableOpacity>
            </View>
          )}
        </View>
      </KeyboardAvoidingView>
    </SafeAreaView>
  );
}