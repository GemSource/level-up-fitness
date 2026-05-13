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

const dayTagColor = (tag: string) => {
  if (tag === 'HIGH') return '#FF7777';
  if (tag === 'LOW') return '#7CFFCB';
  return Colors.primary;
};

export default function WorkoutLog() {
  const { id } = useLocalSearchParams<{ id: string }>();
  const router = useRouter();
  const [workout, setWorkout] = useState<any>(null);
  const [rows, setRows] = useState<any[]>([]);
  const [notes, setNotes] = useState('');
  const [submitting, setSubmitting] = useState(false);

  useEffect(() => {
    (async () => {
      const pid = await AsyncStorage.getItem('profile_id');
      if (!pid || !id) return;
      const w = await getWorkout(pid, id);
      setWorkout(w);
      setRows(w.exercises.map((ex: any) => ({
        name: ex.name,
        target_sets: ex.sets,
        target_reps: ex.reps,
        target_weight: ex.weight,
        target_rpe: ex.target_rpe,
        is_main: !!ex.is_main,
        logged_weight: String(ex.weight),
        logged_reps: String(ex.reps),
        logged_rpe: '',
        done: false,
      })));
    })();
  }, [id]);

  const update = (idx: number, field: string, value: any) => {
    setRows(prev => {
      const next = [...prev];
      next[idx] = { ...next[idx], [field]: value };
      return next;
    });
  };

  const toggleDone = (idx: number) => update(idx, 'done', !rows[idx].done);

  const doneCount = rows.filter(r => r.done).length;
  const total = rows.length;
  const pct = total > 0 ? Math.round((doneCount / total) * 100) : 0;

  const submit = async () => {
    const pid = await AsyncStorage.getItem('profile_id');
    if (!pid) return;
    if (doneCount === 0) {
      return Alert.alert('[SYSTEM]', 'Mark at least one exercise as done.');
    }
    setSubmitting(true);
    try {
      const payload = {
        workout_id: id,
        notes,
        exercises: rows.map(r => ({
          name: r.name,
          target_sets: r.target_sets,
          target_reps: r.target_reps,
          target_weight: r.target_weight,
          target_rpe: r.target_rpe,
          is_main: r.is_main,
          done: r.done,
          logged_weight: r.done && r.logged_weight ? parseFloat(r.logged_weight) : null,
          logged_reps: r.done && r.logged_reps ? parseInt(r.logged_reps) : null,
          logged_rpe: r.done && r.logged_rpe ? parseFloat(r.logged_rpe) : null,
        })),
      };
      const result = await logWorkout(pid, payload);
      let msg = `+${result.xp_gained} XP\nLEVEL ${result.level} · ${result.streak} DAY STREAK\n${result.exercises_done}/${result.exercises_total} EXERCISES\n\n${result.suggestion}`;
      if (result.main_lift_adjustment_kg !== 0 && result.main_lift_adjustment_kg != null) {
        const sign = result.main_lift_adjustment_kg > 0 ? '+' : '';
        msg += `\n\n[ADAPTIVE LOAD]\n${sign}${result.main_lift_adjustment_kg}kg applied to upcoming ${result.main_lift_key} sessions`;
      }
      if (result.new_achievements?.length) {
        msg += '\n\n[ACHIEVEMENTS UNLOCKED]\n' + result.new_achievements.map((a: any) => `★ ${a.name}`).join('\n');
      }
      Alert.alert(
        result.workout_complete ? '[QUEST COMPLETE]' : '[QUEST PROGRESS SAVED]',
        msg,
        [{ text: 'CONTINUE', onPress: () => router.replace('/(tabs)/dashboard') }]
      );
    } catch (e: any) {
      Alert.alert('[SYSTEM ERROR]', e?.response?.data?.detail || e?.message || 'Failed to log');
    } finally {
      setSubmitting(false);
    }
  };

  if (!workout) {
    return <SafeAreaView style={styles.safe}><Text style={styles.system}>[LOADING QUEST...]</Text></SafeAreaView>;
  }

  const dayTag = workout.day_tag || 'BASE';
  const tagColor = dayTagColor(dayTag);

  return (
    <SafeAreaView style={styles.safe}>
      <KeyboardAvoidingView style={{ flex: 1 }} behavior={Platform.OS === 'ios' ? 'padding' : undefined}>
        <View style={styles.header}>
          <TouchableOpacity onPress={() => router.back()} testID="btn-back">
            <Ionicons name="chevron-back" size={24} color={Colors.primary} />
          </TouchableOpacity>
          <View style={{ flex: 1, marginLeft: 8 }}>
            <View style={styles.headTags}>
              <Text style={styles.system}>[W{workout.week} · {workout.week_label}]</Text>
              <View style={[styles.dayTagPill, { borderColor: tagColor }]}>
                <Text style={[styles.dayTagText, { color: tagColor }]}>{dayTag} DAY</Text>
              </View>
            </View>
            <Text style={styles.title}>{workout.day_type.replace('_', ' ')}</Text>
          </View>
        </View>

        {/* Progress bar */}
        <View style={styles.progressWrap}>
          <View style={styles.progressBar}>
            <View style={[styles.progressFill, { width: `${pct}%` }]} />
          </View>
          <Text style={styles.progressTxt}>
            QUEST PROGRESS  ::  {doneCount} / {total}  ({pct}%)
          </Text>
        </View>

        <ScrollView contentContainerStyle={styles.scroll} keyboardShouldPersistTaps="handled">
          {rows.map((r, i) => (
            <SystemFrame
              key={i}
              style={[styles.row, r.done && styles.rowDone]}
              color={r.done ? Colors.questComplete : (r.is_main ? Colors.primary : Colors.border)}
            >
              <View style={styles.rowTop}>
                <TouchableOpacity
                  testID={`exercise-done-${i}`}
                  onPress={() => toggleDone(i)}
                  style={[styles.check, r.done && styles.checkOn]}
                >
                  {r.done && <Ionicons name="checkmark" size={20} color={Colors.questComplete} />}
                </TouchableOpacity>
                <View style={{ flex: 1, marginLeft: 12 }}>
                  <View style={styles.nameRow}>
                    {r.is_main && <Text style={styles.mainStar}>★ </Text>}
                    <Text style={styles.exName}>{r.name}</Text>
                  </View>
                  <Text style={styles.target}>
                    TARGET: {r.target_sets}×{r.target_reps} @ {r.target_weight}kg · RPE {r.target_rpe ?? '-'}
                  </Text>
                </View>
              </View>

              <View style={styles.logGrid}>
                <View style={styles.logCell}>
                  <Text style={styles.logLabel}>WT</Text>
                  <TextInput
                    testID={`ex-wt-${i}`}
                    style={styles.logInput}
                    keyboardType="decimal-pad"
                    value={r.logged_weight}
                    onChangeText={(v) => update(i, 'logged_weight', v)}
                  />
                </View>
                <View style={styles.logCell}>
                  <Text style={styles.logLabel}>REPS</Text>
                  <TextInput
                    testID={`ex-reps-${i}`}
                    style={styles.logInput}
                    keyboardType="number-pad"
                    value={r.logged_reps}
                    onChangeText={(v) => update(i, 'logged_reps', v)}
                  />
                </View>
                <View style={styles.logCell}>
                  <Text style={styles.logLabel}>RPE</Text>
                  <TextInput
                    testID={`ex-rpe-${i}`}
                    style={styles.logInput}
                    keyboardType="decimal-pad"
                    placeholder="-"
                    placeholderTextColor={Colors.textDim}
                    value={r.logged_rpe}
                    onChangeText={(v) => update(i, 'logged_rpe', v)}
                  />
                </View>
              </View>
            </SystemFrame>
          ))}

          <SystemFrame style={styles.notesCard}>
            <Text style={styles.notesLabel}>// QUEST NOTES</Text>
            <TextInput
              testID="input-notes"
              value={notes}
              onChangeText={setNotes}
              multiline
              placeholder="Reflections, fatigue, form notes..."
              placeholderTextColor={Colors.textDim}
              style={styles.notesInput}
            />
          </SystemFrame>

          <TouchableOpacity
            testID="btn-submit-workout"
            style={styles.submit}
            onPress={submit}
            disabled={submitting}
          >
            <Text style={styles.submitTxt}>
              {submitting ? 'TRANSMITTING...' : doneCount === total ? 'COMPLETE QUEST ⚔' : `SAVE PROGRESS  (${doneCount}/${total})`}
            </Text>
          </TouchableOpacity>
        </ScrollView>
      </KeyboardAvoidingView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  safe: { flex: 1, backgroundColor: Colors.bg },
  header: { flexDirection: 'row', alignItems: 'center', padding: 16, paddingBottom: 4 },
  headTags: { flexDirection: 'row', alignItems: 'center', gap: 8 },
  system: { color: Colors.primary, fontFamily: Fonts.mono, fontSize: 10, letterSpacing: 2 },
  dayTagPill: { paddingHorizontal: 6, paddingVertical: 2, borderWidth: 1, backgroundColor: '#000' },
  dayTagText: { fontFamily: Fonts.monoBold, fontSize: 9, letterSpacing: 2 },
  title: { color: Colors.textMain, fontFamily: Fonts.heading, fontSize: 20, letterSpacing: 2, marginTop: 2 },
  progressWrap: { paddingHorizontal: 16, paddingBottom: 8 },
  progressBar: { height: 8, backgroundColor: '#080808', borderWidth: 1, borderColor: Colors.borderGlow, overflow: 'hidden' },
  progressFill: {
    height: '100%', backgroundColor: Colors.questComplete,
    shadowColor: Colors.questComplete, shadowOpacity: 1, shadowRadius: 8,
  },
  progressTxt: { color: Colors.textMuted, fontFamily: Fonts.monoBold, fontSize: 10, letterSpacing: 2, marginTop: 6 },
  scroll: { padding: 16, paddingBottom: 60 },
  row: { marginBottom: 10 },
  rowDone: { opacity: 0.85 },
  rowTop: { flexDirection: 'row', alignItems: 'flex-start' },
  check: { width: 36, height: 36, borderWidth: 1, borderColor: Colors.border, alignItems: 'center', justifyContent: 'center', backgroundColor: '#000' },
  checkOn: { borderColor: Colors.questComplete, backgroundColor: 'rgba(0,255,0,0.08)', shadowColor: Colors.questComplete, shadowOpacity: 0.6, shadowRadius: 8 },
  nameRow: { flexDirection: 'row', alignItems: 'center' },
  mainStar: { color: Colors.primary, fontFamily: Fonts.monoBold, fontSize: 14 },
  exName: { color: Colors.textMain, fontFamily: Fonts.heading, fontSize: 16, letterSpacing: 1 },
  target: { color: Colors.textMuted, fontFamily: Fonts.mono, fontSize: 11, marginTop: 4, letterSpacing: 1 },
  logGrid: { flexDirection: 'row', gap: 8, marginTop: 12 },
  logCell: { flex: 1 },
  logLabel: { color: Colors.primary, fontFamily: Fonts.monoBold, fontSize: 9, letterSpacing: 2, marginBottom: 4 },
  logInput: {
    backgroundColor: '#000', borderWidth: 1, borderColor: Colors.border,
    color: Colors.textMain, fontFamily: Fonts.mono, fontSize: 14, padding: 8, textAlign: 'center',
  },
  notesCard: { marginTop: 8 },
  notesLabel: { color: Colors.primary, fontFamily: Fonts.monoBold, fontSize: 11, letterSpacing: 2, marginBottom: 8 },
  notesInput: { backgroundColor: '#000', borderWidth: 1, borderColor: Colors.border, color: Colors.textMain, fontFamily: Fonts.mono, fontSize: 12, padding: 10, minHeight: 60 },
  submit: { marginTop: 12, backgroundColor: 'rgba(0,255,255,0.1)', borderWidth: 1, borderColor: Colors.primary, paddingVertical: 16, alignItems: 'center', shadowColor: Colors.primary, shadowOpacity: 0.5, shadowRadius: 12 },
  submitTxt: { color: Colors.primary, fontFamily: Fonts.heading, fontSize: 14, letterSpacing: 3 },
});
