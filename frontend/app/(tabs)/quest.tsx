import React, { useCallback, useState } from 'react';
import { View, Text, StyleSheet, ScrollView, TouchableOpacity } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { useFocusEffect, useRouter } from 'expo-router';
import AsyncStorage from '@react-native-async-storage/async-storage';
import { Ionicons } from '@expo/vector-icons';
import { Colors, Fonts } from '../../src/theme';
import { SystemFrame } from '../../src/components/SystemFrame';
import { listWorkouts } from '../../src/api';

export default function QuestList() {
  const router = useRouter();
  const [workouts, setWorkouts] = useState<any[]>([]);
  const [filterWeek, setFilterWeek] = useState<number | null>(null);

  const load = async () => {
    const id = await AsyncStorage.getItem('profile_id');
    if (!id) { router.replace('/onboarding'); return; }
    const ws = await listWorkouts(id);
    setWorkouts(ws);
  };

  useFocusEffect(useCallback(() => { load(); }, []));

  const filtered = filterWeek ? workouts.filter(w => w.week === filterWeek) : workouts;
  const weeks = Array.from(new Set(workouts.map(w => w.week))).sort();

  return (
    <SafeAreaView style={styles.safe}>
      <View style={styles.header}>
        <Text style={styles.system}>[QUEST LOG]</Text>
        <Text style={styles.title}>TRAINING BLOCK</Text>
      </View>
      <View style={styles.weekRow}>
        <TouchableOpacity
          testID="filter-all"
          onPress={() => setFilterWeek(null)}
          style={[styles.weekPill, filterWeek === null && styles.weekPillActive]}
        >
          <Text style={[styles.weekText, filterWeek === null && styles.weekTextActive]}>ALL</Text>
        </TouchableOpacity>
        {weeks.map(w => (
          <TouchableOpacity
            key={w}
            testID={`filter-week-${w}`}
            onPress={() => setFilterWeek(w)}
            style={[styles.weekPill, filterWeek === w && styles.weekPillActive]}
          >
            <Text style={[styles.weekText, filterWeek === w && styles.weekTextActive]}>W{w}</Text>
          </TouchableOpacity>
        ))}
      </View>
      <ScrollView contentContainerStyle={{ padding: 16, paddingBottom: 40 }}>
        {filtered.map((w) => (
          <TouchableOpacity
            key={w.id}
            testID={`workout-${w.id}`}
            onPress={() => router.push(`/workout/${w.id}`)}
            style={{ marginBottom: 10 }}
            disabled={w.completed}
          >
            <SystemFrame style={[styles.card, w.completed && styles.cardDone]} color={w.completed ? Colors.questComplete : Colors.primary}>
              <View style={styles.cardHead}>
                <Text style={[styles.weekLabel, w.completed && { color: Colors.questComplete }]}>
                  W{w.week} · {w.week_label}
                </Text>
                {w.completed ? (
                  <Ionicons name="checkmark-circle" size={20} color={Colors.questComplete} />
                ) : (
                  <Ionicons name="chevron-forward" size={20} color={Colors.primary} />
                )}
              </View>
              <Text style={styles.dayType}>{w.day_type.replace('_', ' ')}</Text>
              <Text style={styles.exCount}>{w.exercises.length} EXERCISES</Text>
            </SystemFrame>
          </TouchableOpacity>
        ))}
      </ScrollView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  safe: { flex: 1, backgroundColor: Colors.bg },
  header: { padding: 16, paddingBottom: 8 },
  system: { color: Colors.primary, fontFamily: Fonts.mono, fontSize: 10, letterSpacing: 3 },
  title: { color: Colors.textMain, fontFamily: Fonts.heading, fontSize: 22, letterSpacing: 1, marginTop: 2 },
  weekRow: { flexDirection: 'row', gap: 6, paddingHorizontal: 16, paddingBottom: 10, flexWrap: 'wrap' },
  weekPill: { paddingHorizontal: 12, paddingVertical: 6, borderWidth: 1, borderColor: Colors.border, backgroundColor: '#000' },
  weekPillActive: { borderColor: Colors.primary, backgroundColor: 'rgba(0,255,255,0.08)' },
  weekText: { color: Colors.textMuted, fontFamily: Fonts.monoBold, fontSize: 11, letterSpacing: 1 },
  weekTextActive: { color: Colors.primary },
  card: {},
  cardDone: { opacity: 0.6 },
  cardHead: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center' },
  weekLabel: { color: Colors.primary, fontFamily: Fonts.monoBold, fontSize: 10, letterSpacing: 2 },
  dayType: { color: Colors.textMain, fontFamily: Fonts.heading, fontSize: 18, letterSpacing: 2, marginTop: 4 },
  exCount: { color: Colors.textMuted, fontFamily: Fonts.mono, fontSize: 10, letterSpacing: 1, marginTop: 4 },
});
