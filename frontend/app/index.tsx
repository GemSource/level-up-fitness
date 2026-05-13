import React, { useEffect } from 'react';
import { View, ActivityIndicator, StyleSheet } from 'react-native';
import { useRouter } from 'expo-router';
import AsyncStorage from '@react-native-async-storage/async-storage';
import { Colors } from '../src/theme';

export default function Index() {
  const router = useRouter();

  useEffect(() => {
    (async () => {
      try {
        const id = await AsyncStorage.getItem('profile_id');
        if (id) {
          router.replace('/(tabs)/dashboard');
        } else {
          router.replace('/onboarding');
        }
      } catch {
        router.replace('/onboarding');
      }
    })();
  }, []);

  return (
    <View testID="splash-screen" style={styles.container}>
      <ActivityIndicator color={Colors.primary} />
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: Colors.bg, alignItems: 'center', justifyContent: 'center' },
});
