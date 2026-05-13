import React, { useEffect, useState } from 'react';
import {
  View, Text, StyleSheet, ScrollView, TextInput, TouchableOpacity,
  KeyboardAvoidingView, Platform, Alert,
} from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { useLocalSearchParams, useRouter } from 'expo-router';
import AsyncStorage from '@react-native-async-storage/async-storage';
import { Ionicons } from '@expo/vector-icons';
import { Colors, Fonts } from '../../src/theme';
import { SystemFrame } from '../../src/components/SystemFrame';
import { getWorkout, logWorkout } from '../../src/api';

export default function WorkoutLog() {
  const { id } = useLocalSearchParams<{ id: string }>();
  const router = useRouter();
  const [workout, setWorkout] = useState<any>(null);
  const [logs, setLogs] = useState<any[]>([]);
  const [notes, setNotes] = useState('');
  const [submitting, setSubmitting] = useState(false);

  useEffect(() => {
    (async () => {
      const pid = await AsyncStorage.getItem('profile_id');
      if (!pid || !id) return;
      const w = await getWorkout(pid, id);
      setWorkout(w);
      setLogs(w.exercises.map((ex: any) => ({
        name: ex.name,
        target_sets: ex.sets,
        target_reps: ex.reps,
        target_weight: ex.weight,
        target_rpe: ex.target_rpe,
        sets: Array.from({ length: ex.sets }, () => ({
          weight: String(ex.weight),
          reps: String(ex.reps),
          rpe: '',
          completed: false,
        })),
      })));
    })();
  }, [id]);

  const updateSet = (exIdx: number, setIdx: number, field: string, value: any) => {
    const next = [...logs];
    next[exIdx].sets[setIdx] = { ...next[exIdx].sets[setIdx], [field]: value };
    setLogs(next);
  };

  const toggleSet = (exIdx: number, setIdx: number) => {
    const next = [...logs];
    next[exIdx].sets[setIdx].completed = !next[exIdx].sets[setIdx].completed;
    setLogs(next);
  };

  const submit = async () => {
    const pid = await AsyncStorage.getItem('profile_id');
    if (!pid) return;
    const anyCompleted = logs.some(ex => ex.sets.some((s: any) => s.completed));
    if (!anyCompleted) {
      return Alert.alert('[SYSTEM]', 'Mark at least one set as complete.');
    }
    setSubmitting(true);
    try {
      const payload = {
        workout_id: id,
        notes,
        exercises: logs.map(ex => ({
          name: ex.name,
          target_sets: ex.target_sets,
          target_reps: ex.target_reps,
          target_weight: ex.target_weight,
          target_rpe: ex.target_rpe,
          sets: ex.sets.map((s: any) => ({
            weight: parseFloat(s.weight) || 0,
            reps: parseInt(s.reps) || 0,
            rpe: s.rpe ? parseFloat(s.rpe) : null,
            completed: !!s.completed,
          })),
        })),
      };
      const result = await logWorkout(pid, payload);
      let msg = `+${result.xp_gained} XP\nLEVEL ${result.level} · ${result.streak} DAY STREAK\n\n${result.suggestion}`;
      if (result.new_achievements?.length) {
        msg += '\n\n[ACHIEVEMENTS UNLOCKED]\n' + result.new_achievements.map((a: any) => `★ ${a.name}`).join('\n');
      }
      Alert.alert('[QUEST COMPLETE]', msg, [
        { text: 'CONTINUE', onPress: () => router.replace('/(tabs)/dashboard') },
      ]);
    } catch (e: any) {
      Alert.alert('[SYSTEM ERROR]', e?.response?.data?.detail || e?.message || 'Failed to log');
    } finally {
      setSubmitting(false);
    }
  };

  if (!workout) {
    return <SafeAreaView style={styles.safe}><Text style={styles.system}>[LOADING QUEST...]</Text></SafeAreaView>;
  }

  return (
    <SafeAreaView style={styles.safe}>
      <KeyboardAvoidingView style={{ flex: 1 }} behavior={Platform.OS === 'ios' ? 'padding' : undefined}>
        <View style={styles.header}>
          <TouchableOpacity onPress={() => router.back()} testID="btn-back">
            <Ionicons name="chevron-back" size={24} color={Colors.primary} />
          </TouchableOpacity>
          <View style={{ flex: 1, marginLeft: 8 }}>
            <Text style={styles.system}>[QUEST :: W{workout.week} · {workout.week_label}]</Text>
            <Text style={styles.title}>{workout.day_type.replace('_', ' ')}</Text>
          </View>
        </View>

        <ScrollView contentContainerStyle={styles.scroll} keyboardShouldPersistTaps="handled">
          {logs.map((ex, exIdx) => (
            <SystemFrame key={exIdx} style={styles.exCard}>
              <View style={styles.exHead}>
                <Text style={styles.exName}>{ex.name}</Text>
                <Text style={styles.exTarget}>RPE {ex.target_rpe ?? '-'}</Text>
              </View>
              <Text style={styles.exSub}>TARGET: {ex.target_sets} × {ex.target_reps} @ {ex.target_weight}kg</Text>
              <View style={styles.setHead}>
                <Text style={styles.setHeadTxt}>SET</Text>
                <Text style={styles.setHeadTxt}>KG</Text>
                <Text style={styles.setHeadTxt}>REPS</Text>
                <Text style={styles.setHeadTxt}>RPE</Text>
                <Text style={styles.setHeadTxt}>✓</Text>
              </View>
              {ex.sets.map((s: any, setIdx: number) => (
                <View key={setIdx} style={styles.setRow}>
                  <Text style={styles.setIdx}>{setIdx + 1}</Text>
                  <TextInput
                    testID={`set-weight-${exIdx}-${setIdx}`}
                    style={styles.setInput}
                    keyboardType="decimal-pad"
                    value={s.weight}
                    onChangeText={(v) => updateSet(exIdx, setIdx, 'weight', v)}
                  />
                  <TextInput
                    testID={`set-reps-${exIdx}-${setIdx}`}
                    style={styles.setInput}
                    keyboardType="number-pad"
                    value={s.reps}
                    onChangeText={(v) => updateSet(exIdx, setIdx, 'reps', v)}
                  />
                  <TextInput
                    testID={`set-rpe-${exIdx}-${setIdx}`}
                    style={styles.setInput}
                    keyboardType="decimal-pad"
                    placeholder="-"
                    placeholderTextColor={Colors.textDim}
                    value={s.rpe}
                    onChangeText={(v) => updateSet(exIdx, setIdx, 'rpe', v)}
                  />
                  <TouchableOpacity
                    testID={`set-done-${exIdx}-${setIdx}`}
                    onPress={() => toggleSet(exIdx, setIdx)}
                    style={[styles.checkBox, s.completed && styles.checkBoxOn]}
                  >
                    {s.completed && <Ionicons name="checkmark" size={16} color={Colors.questComplete} />}
                  </TouchableOpacity>
                </View>
              ))}
            </SystemFrame>
          ))}

          <SystemFrame style={styles.exCard}>
            <Text style={styles.label}>// QUEST NOTES</Text>
            <TextInput
              testID="input-notes"
              value={notes}
              onChangeText={setNotes}
              multiline
              placeholder="Reflections, fatigue, form notes..."
              placeholderTextColor={Colors.textDim}
              style={styles.notes}
            />
          </SystemFrame>

          <TouchableOpacity
            testID="btn-submit-workout"
            style={styles.submit}
            onPress={submit}
            disabled={submitting}
          >
            <Text style={styles.submitTxt}>{submitting ? 'TRANSMITTING...' : 'COMPLETE QUEST ⚔'}</Text>
          </TouchableOpacity>
        </ScrollView>
      </KeyboardAvoidingView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  safe: { flex: 1, backgroundColor: Colors.bg },
  header: { flexDirection: 'row', alignItems: 'center', padding: 16, paddingBottom: 8 },
  system: { color: Colors.primary, fontFamily: Fonts.mono, fontSize: 10, letterSpacing: 2 },
  title: { color: Colors.textMain, fontFamily: Fonts.heading, fontSize: 20, letterSpacing: 2, marginTop: 2 },
  scroll: { padding: 16, paddingBottom: 60 },
  exCard: { marginBottom: 12 },
  exHead: { flexDirection: 'row', justifyContent: 'space-between' },
  exName: { color: Colors.textMain, fontFamily: Fonts.heading, fontSize: 16, letterSpacing: 1 },
  exTarget: { color: Colors.primary, fontFamily: Fonts.monoBold, fontSize: 11 },
  exSub: { color: Colors.textMuted, fontFamily: Fonts.mono, fontSize: 10, letterSpacing: 1, marginTop: 4, marginBottom: 10 },
  setHead: { flexDirection: 'row', borderBottomWidth: 1, borderBottomColor: Colors.border, paddingBottom: 4 },
  setHeadTxt: { color: Colors.textMuted, fontFamily: Fonts.monoBold, fontSize: 10, letterSpacing: 1, flex: 1, textAlign: 'center' },
  setRow: { flexDirection: 'row', alignItems: 'center', paddingVertical: 6 },
  setIdx: { color: Colors.primary, fontFamily: Fonts.monoBold, fontSize: 12, flex: 1, textAlign: 'center' },
  setInput: {
    flex: 1,
    marginHorizontal: 2,
    backgroundColor: '#000',
    borderWidth: 1,
    borderColor: Colors.border,
    color: Colors.textMain,
    fontFamily: Fonts.mono,
    fontSize: 12,
    textAlign: 'center',
    paddingVertical: 6,
  },
  checkBox: { flex: 1, alignItems: 'center', justifyContent: 'center', borderWidth: 1, borderColor: Colors.border, height: 30, marginHorizontal: 2 },
  checkBoxOn: { borderColor: Colors.questComplete, backgroundColor: 'rgba(0,255,0,0.08)' },
  label: { color: Colors.primary, fontFamily: Fonts.monoBold, fontSize: 11, letterSpacing: 2, marginBottom: 8 },
  notes: { backgroundColor: '#000', borderWidth: 1, borderColor: Colors.border, color: Colors.textMain, fontFamily: Fonts.mono, fontSize: 12, padding: 10, minHeight: 60 },
  submit: { backgroundColor: 'rgba(0,255,255,0.1)', borderWidth: 1, borderColor: Colors.primary, paddingVertical: 16, alignItems: 'center', marginTop: 8, shadowColor: Colors.primary, shadowOpacity: 0.5, shadowRadius: 12 },
  submitTxt: { color: Colors.primary, fontFamily: Fonts.heading, fontSize: 16, letterSpacing: 3 },
});
