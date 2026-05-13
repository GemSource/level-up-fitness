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
import { listSideQuests, logSideQuest } from '../../src/api';

export default function SideQuestLog() {
  const { id } = useLocalSearchParams<{ id: string }>();
  const router = useRouter();
  const [quest, setQuest] = useState<any>(null);
  const [rows, setRows] = useState<any[]>([]);
  const [notes, setNotes] = useState('');
  const [submitting, setSubmitting] = useState(false);

  useEffect(() => {
    (async () => {
      const pid = await AsyncStorage.getItem('profile_id');
      if (!pid || !id) return;
      const list = await listSideQuests(pid);
      const q = list.find((x: any) => x.id === id);
      if (!q) return;
      setQuest(q);
      setRows(q.exercises.map((ex: any) => ({
        name: ex.name,
        target_sets: ex.sets,
        target_reps: ex.reps,
        target_weight: ex.weight,
        target_rpe: ex.target_rpe,
        is_main_compound: !!ex.is_main_compound,
        logged_weight: String(ex.weight || ''),
        logged_reps: String(ex.reps || ''),
        logged_rpe: '',
        done: false,
      })));
    })();
  }, [id]);

  const toggle = (i: number) => {
    const n = [...rows];
    n[i] = { ...n[i], done: !n[i].done };
    setRows(n);
  };
  const update = (i: number, key: string, val: any) => {
    const n = [...rows];
    n[i] = { ...n[i], [key]: val };
    setRows(n);
  };

  const done = rows.filter(r => r.done).length;
  const total = rows.length;
  const pct = total ? Math.round((done / total) * 100) : 0;

  const submit = async () => {
    const pid = await AsyncStorage.getItem('profile_id');
    if (!pid || !id) return;
    if (done === 0) return Alert.alert('[SYSTEM]', 'Tick at least one exercise.');
    setSubmitting(true);
    try {
      const payload = {
        quest_id: id,
        notes,
        exercises: rows.map(r => ({
          name: r.name,
          target_sets: r.target_sets,
          target_reps: r.target_reps,
          target_weight: r.target_weight,
          target_rpe: r.target_rpe,
          is_main_compound: r.is_main_compound,
          done: r.done,
          logged_weight: r.done && r.logged_weight ? parseFloat(r.logged_weight) : null,
          logged_reps: r.done && r.logged_reps ? parseInt(r.logged_reps) : null,
          logged_rpe: r.done && r.logged_rpe ? parseFloat(r.logged_rpe) : null,
        })),
      };
      const result = await logSideQuest(pid, payload);
      // Navigate first (web's Alert.alert ignores button onPress), then show toast/alert
      router.replace('/side-quests');
      setTimeout(() => Alert.alert(
        result.side_quest_complete ? '[SIDE QUEST CLEARED]' : '[PROGRESS SAVED]',
        `+${result.xp_gained} XP · LV ${result.level}\n${result.exercises_done}/${result.exercises_total} EXERCISES`,
      ), 100);
    } catch (e: any) {
      Alert.alert('[SYSTEM ERROR]', e?.response?.data?.detail?.message || e?.message || 'Failed');
    } finally {
      setSubmitting(false);
    }
  };

  if (!quest) return <SafeAreaView style={styles.safe}><Text style={styles.system}>[LOADING...]</Text></SafeAreaView>;

  return (
    <SafeAreaView style={styles.safe}>
      <KeyboardAvoidingView style={{ flex: 1 }} behavior={Platform.OS === 'ios' ? 'padding' : undefined}>
        <View style={styles.header}>
          <TouchableOpacity onPress={() => router.back()} testID="btn-back">
            <Ionicons name="chevron-back" size={24} color={Colors.primary} />
          </TouchableOpacity>
          <View style={{ flex: 1, marginLeft: 8 }}>
            <Text style={styles.system}>[SIDE QUEST]</Text>
            <Text style={styles.title}>{quest.name}</Text>
          </View>
        </View>

        <View style={styles.progressWrap}>
          <View style={styles.bar}>
            <View style={[styles.barFill, { width: `${pct}%` }]} />
          </View>
          <Text style={styles.progressTxt}>SIDE QUEST PROGRESS  ::  {done} / {total}  ({pct}%)</Text>
        </View>

        <ScrollView contentContainerStyle={styles.scroll} keyboardShouldPersistTaps="handled">
          {rows.map((r, i) => (
            <SystemFrame
              key={i}
              style={[styles.row, r.done && styles.rowDone]}
              color={r.done ? Colors.questComplete : (r.is_main_compound ? Colors.primary : Colors.border)}
            >
              <View style={styles.rowTop}>
                <TouchableOpacity
                  testID={`sq-ex-done-${i}`}
                  onPress={() => toggle(i)}
                  style={[styles.check, r.done && styles.checkOn]}
                >
                  {r.done && <Ionicons name="checkmark" size={20} color={Colors.questComplete} />}
                </TouchableOpacity>
                <View style={{ flex: 1, marginLeft: 12 }}>
                  <Text style={styles.exName}>{r.is_main_compound ? '★ ' : ''}{r.name}</Text>
                  <Text style={styles.target}>
                    TARGET: {r.target_sets}×{r.target_reps} @ {r.target_weight}kg · RPE {r.target_rpe ?? '-'}
                  </Text>
                </View>
              </View>
              <View style={styles.grid}>
                <View style={styles.cell}>
                  <Text style={styles.cellLabel}>WT</Text>
                  <TextInput
                    testID={`sq-wt-${i}`}
                    style={styles.cellInput}
                    keyboardType="decimal-pad"
                    value={r.logged_weight}
                    onChangeText={(v) => update(i, 'logged_weight', v)}
                  />
                </View>
                <View style={styles.cell}>
                  <Text style={styles.cellLabel}>REPS</Text>
                  <TextInput
                    testID={`sq-reps-${i}`}
                    style={styles.cellInput}
                    keyboardType="number-pad"
                    value={r.logged_reps}
                    onChangeText={(v) => update(i, 'logged_reps', v)}
                  />
                </View>
                <View style={styles.cell}>
                  <Text style={styles.cellLabel}>RPE</Text>
                  <TextInput
                    testID={`sq-rpe-${i}`}
                    style={styles.cellInput}
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

          <SystemFrame style={{ marginTop: 8 }}>
            <Text style={styles.label}>// NOTES</Text>
            <TextInput
              testID="input-notes"
              value={notes}
              onChangeText={setNotes}
              multiline
              placeholder="Reflections..."
              placeholderTextColor={Colors.textDim}
              style={styles.notes}
            />
          </SystemFrame>

          <TouchableOpacity
            testID="btn-submit-sq"
            style={styles.submit}
            onPress={submit}
            disabled={submitting}
          >
            <Text style={styles.submitTxt}>
              {submitting ? 'TRANSMITTING...' : done === total ? 'COMPLETE SIDE QUEST ⚔' : `SAVE PROGRESS  (${done}/${total})`}
            </Text>
          </TouchableOpacity>
        </ScrollView>
      </KeyboardAvoidingView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  safe: { flex: 1, backgroundColor: Colors.bg },
  header: { flexDirection: 'row', alignItems: 'center', padding: 16, paddingBottom: 6 },
  system: { color: Colors.primary, fontFamily: Fonts.mono, fontSize: 10, letterSpacing: 2 },
  title: { color: Colors.textMain, fontFamily: Fonts.heading, fontSize: 18, letterSpacing: 2, marginTop: 2 },
  progressWrap: { paddingHorizontal: 16, paddingBottom: 10 },
  bar: { height: 8, backgroundColor: '#080808', borderWidth: 1, borderColor: Colors.borderGlow, overflow: 'hidden' },
  barFill: { height: '100%', backgroundColor: Colors.questComplete, shadowColor: Colors.questComplete, shadowOpacity: 1, shadowRadius: 8 },
  progressTxt: { color: Colors.textMuted, fontFamily: Fonts.monoBold, fontSize: 10, letterSpacing: 2, marginTop: 6 },
  scroll: { padding: 16, paddingBottom: 60 },
  row: { marginBottom: 10 },
  rowDone: { opacity: 0.85 },
  rowTop: { flexDirection: 'row', alignItems: 'flex-start' },
  check: { width: 36, height: 36, borderWidth: 1, borderColor: Colors.border, alignItems: 'center', justifyContent: 'center', backgroundColor: '#000' },
  checkOn: { borderColor: Colors.questComplete, backgroundColor: 'rgba(0,255,0,0.08)' },
  exName: { color: Colors.textMain, fontFamily: Fonts.heading, fontSize: 14, letterSpacing: 1 },
  target: { color: Colors.textMuted, fontFamily: Fonts.mono, fontSize: 10, marginTop: 4 },
  grid: { flexDirection: 'row', gap: 8, marginTop: 10 },
  cell: { flex: 1 },
  cellLabel: { color: Colors.primary, fontFamily: Fonts.monoBold, fontSize: 9, letterSpacing: 1, marginBottom: 4 },
  cellInput: { backgroundColor: '#000', borderWidth: 1, borderColor: Colors.border, color: Colors.textMain, fontFamily: Fonts.mono, fontSize: 13, padding: 6, textAlign: 'center' },
  label: { color: Colors.primary, fontFamily: Fonts.monoBold, fontSize: 11, letterSpacing: 2, marginBottom: 8 },
  notes: { backgroundColor: '#000', borderWidth: 1, borderColor: Colors.border, color: Colors.textMain, fontFamily: Fonts.mono, fontSize: 12, padding: 10, minHeight: 50 },
  submit: { backgroundColor: 'rgba(0,255,255,0.1)', borderWidth: 1, borderColor: Colors.primary, paddingVertical: 14, alignItems: 'center', marginTop: 8 },
  submitTxt: { color: Colors.primary, fontFamily: Fonts.heading, fontSize: 14, letterSpacing: 3 },
});
