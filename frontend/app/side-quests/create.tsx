import React, { useEffect, useState, useMemo } from 'react';
import {
  View, Text, StyleSheet, ScrollView, TextInput, TouchableOpacity,
  KeyboardAvoidingView, Platform, Alert,
} from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { useRouter } from 'expo-router';
import AsyncStorage from '@react-native-async-storage/async-storage';
import { Ionicons } from '@expo/vector-icons';
import { Colors, Fonts } from '../../src/theme';
import { SystemFrame } from '../../src/components/SystemFrame';
import { listExercises, createSideQuest } from '../../src/api';

export default function CreateSideQuest() {
  const router = useRouter();
  const [name, setName] = useState('');
  const [library, setLibrary] = useState<any[]>([]);
  const [search, setSearch] = useState('');
  const [activeCat, setActiveCat] = useState('all');
  const [picked, setPicked] = useState<any[]>([]);
  const [submitting, setSubmitting] = useState(false);

  useEffect(() => {
    (async () => {
      const pid = await AsyncStorage.getItem('profile_id');
      const list = await listExercises(pid || undefined);
      setLibrary(list);
    })();
  }, []);

  const categories = useMemo(() => ['all', ...Array.from(new Set(library.map(e => e.category)))], [library]);
  const filtered = useMemo(() => library.filter(e => {
    if (activeCat !== 'all' && e.category !== activeCat) return false;
    if (search && !e.name.toLowerCase().includes(search.toLowerCase())) return false;
    return true;
  }), [library, search, activeCat]);

  const addExercise = (e: any) => {
    if (picked.find(p => p.name === e.name)) return;
    setPicked([...picked, { name: e.name, sets: 3, reps: 10, weight: 0, target_rpe: 7, is_main_compound: !!e.is_main_compound }]);
  };

  const removeExercise = (i: number) => setPicked(picked.filter((_, idx) => idx !== i));
  const update = (i: number, key: string, val: any) => {
    const next = [...picked];
    next[i] = { ...next[i], [key]: val };
    setPicked(next);
  };

  const save = async () => {
    if (!name.trim()) return Alert.alert('[SYSTEM]', 'Name your side quest.');
    if (picked.length < 3) return Alert.alert('[SYSTEM]', 'Side quest requires at least 3 exercises.');
    const pid = await AsyncStorage.getItem('profile_id');
    if (!pid) return;
    setSubmitting(true);
    try {
      const payload = {
        name: name.trim(),
        exercises: picked.map(p => ({
          name: p.name,
          sets: parseInt(String(p.sets)) || 3,
          reps: parseInt(String(p.reps)) || 10,
          weight: parseFloat(String(p.weight)) || 0,
          target_rpe: p.target_rpe ? parseFloat(String(p.target_rpe)) : null,
          is_main_compound: p.is_main_compound,
        })),
      };
      const sq = await createSideQuest(pid, payload);
      // Navigate first (web's Alert.alert ignores button onPress), then show toast/alert
      router.replace(`/side-quests/${sq.id}`);
      setTimeout(() => Alert.alert('[SIDE QUEST FORGED]', `"${sq.name}" ready to log.`), 100);
    } catch (e: any) {
      Alert.alert('[SYSTEM ERROR]', e?.response?.data?.detail?.message || e?.message || 'Failed');
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <SafeAreaView style={styles.safe}>
      <KeyboardAvoidingView style={{ flex: 1 }} behavior={Platform.OS === 'ios' ? 'padding' : undefined}>
        <View style={styles.header}>
          <TouchableOpacity onPress={() => router.back()} testID="btn-back">
            <Ionicons name="chevron-back" size={24} color={Colors.primary} />
          </TouchableOpacity>
          <View style={{ flex: 1, marginLeft: 8 }}>
            <Text style={styles.system}>[FORGE]</Text>
            <Text style={styles.title}>NEW SIDE QUEST</Text>
          </View>
        </View>

        <ScrollView contentContainerStyle={styles.scroll} keyboardShouldPersistTaps="handled">
          <SystemFrame style={styles.frame}>
            <Text style={styles.label}>// QUEST NAME</Text>
            <TextInput
              testID="input-name"
              value={name}
              onChangeText={setName}
              placeholder="e.g. Arm Annihilation"
              placeholderTextColor={Colors.textDim}
              style={styles.input}
            />
          </SystemFrame>

          <Text style={styles.label}>// SELECTED ({picked.length} / min 3)</Text>
          {picked.length === 0 && (
            <Text style={styles.placeholder}>Tap exercises below to add them.</Text>
          )}
          {picked.map((p, i) => (
            <SystemFrame key={i} style={styles.pickedCard}>
              <View style={styles.pickedHead}>
                <Text style={styles.pickedName}>{p.is_main_compound ? '★ ' : ''}{p.name}</Text>
                <TouchableOpacity onPress={() => removeExercise(i)} testID={`remove-${i}`}>
                  <Ionicons name="close" size={20} color={Colors.danger} />
                </TouchableOpacity>
              </View>
              <View style={styles.row3}>
                <View style={styles.cell}>
                  <Text style={styles.cellLabel}>SETS</Text>
                  <TextInput
                    testID={`sets-${i}`}
                    style={styles.cellInput}
                    keyboardType="number-pad"
                    value={String(p.sets)}
                    onChangeText={(v) => update(i, 'sets', v)}
                  />
                </View>
                <View style={styles.cell}>
                  <Text style={styles.cellLabel}>REPS</Text>
                  <TextInput
                    testID={`reps-${i}`}
                    style={styles.cellInput}
                    keyboardType="number-pad"
                    value={String(p.reps)}
                    onChangeText={(v) => update(i, 'reps', v)}
                  />
                </View>
                <View style={styles.cell}>
                  <Text style={styles.cellLabel}>KG</Text>
                  <TextInput
                    testID={`weight-${i}`}
                    style={styles.cellInput}
                    keyboardType="decimal-pad"
                    value={String(p.weight)}
                    onChangeText={(v) => update(i, 'weight', v)}
                  />
                </View>
                <View style={styles.cell}>
                  <Text style={styles.cellLabel}>RPE</Text>
                  <TextInput
                    testID={`rpe-${i}`}
                    style={styles.cellInput}
                    keyboardType="decimal-pad"
                    value={String(p.target_rpe || '')}
                    onChangeText={(v) => update(i, 'target_rpe', v)}
                  />
                </View>
              </View>
            </SystemFrame>
          ))}

          <TouchableOpacity
            testID="btn-save-sq"
            style={[styles.saveBtn, picked.length < 3 && styles.saveBtnLocked]}
            onPress={save}
            disabled={submitting || picked.length < 3}
          >
            <Text style={[styles.saveTxt, picked.length < 3 && { color: Colors.textDim }]}>
              {submitting ? 'SAVING...' : picked.length < 3 ? `ADD ${3 - picked.length} MORE` : 'FORGE QUEST ⚔'}
            </Text>
          </TouchableOpacity>

          <Text style={[styles.label, { marginTop: 24 }]}>// EXERCISE LIBRARY</Text>
          <TextInput
            testID="input-search"
            value={search}
            onChangeText={setSearch}
            placeholder="Search exercises..."
            placeholderTextColor={Colors.textDim}
            style={styles.input}
          />
          <ScrollView horizontal showsHorizontalScrollIndicator={false} contentContainerStyle={styles.catRow}>
            {categories.map(c => (
              <TouchableOpacity
                key={c}
                onPress={() => setActiveCat(c)}
                testID={`cat-${c}`}
                style={[styles.catPill, activeCat === c && styles.catActive]}
              >
                <Text style={[styles.catTxt, activeCat === c && styles.catTxtActive]}>{c.toUpperCase()}</Text>
              </TouchableOpacity>
            ))}
          </ScrollView>

          {filtered.map((e, idx) => (
            <TouchableOpacity
              key={`${e.name}-${idx}`}
              testID={`lib-${e.name.replace(/\s+/g, '-').toLowerCase()}`}
              onPress={() => addExercise(e)}
              style={styles.libRow}
            >
              <View style={{ flex: 1 }}>
                <Text style={styles.libName}>{e.is_main_compound ? '★ ' : ''}{e.name}</Text>
                <Text style={styles.libMeta}>{e.category} · {e.muscle_group} · {e.equipment}</Text>
              </View>
              <Ionicons name="add-circle-outline" size={22} color={Colors.primary} />
            </TouchableOpacity>
          ))}
        </ScrollView>
      </KeyboardAvoidingView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  safe: { flex: 1, backgroundColor: Colors.bg },
  header: { flexDirection: 'row', alignItems: 'center', padding: 16 },
  system: { color: Colors.primary, fontFamily: Fonts.mono, fontSize: 10, letterSpacing: 2 },
  title: { color: Colors.textMain, fontFamily: Fonts.heading, fontSize: 20, letterSpacing: 2, marginTop: 2 },
  scroll: { padding: 16, paddingBottom: 40 },
  frame: { marginBottom: 12 },
  label: { color: Colors.primary, fontFamily: Fonts.monoBold, fontSize: 11, letterSpacing: 2, marginBottom: 8 },
  input: { backgroundColor: '#000', borderWidth: 1, borderColor: Colors.borderGlow, color: Colors.textMain, fontFamily: Fonts.mono, fontSize: 14, padding: 12 },
  placeholder: { color: Colors.textDim, fontFamily: Fonts.mono, fontSize: 12, fontStyle: 'italic', marginBottom: 10 },
  pickedCard: { marginBottom: 10 },
  pickedHead: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center' },
  pickedName: { color: Colors.textMain, fontFamily: Fonts.heading, fontSize: 14, letterSpacing: 1, flex: 1 },
  row3: { flexDirection: 'row', gap: 6, marginTop: 8 },
  cell: { flex: 1 },
  cellLabel: { color: Colors.primary, fontFamily: Fonts.monoBold, fontSize: 9, letterSpacing: 1, marginBottom: 4 },
  cellInput: { backgroundColor: '#000', borderWidth: 1, borderColor: Colors.border, color: Colors.textMain, fontFamily: Fonts.mono, fontSize: 12, padding: 6, textAlign: 'center' },
  saveBtn: { backgroundColor: 'rgba(0,255,255,0.1)', borderWidth: 1, borderColor: Colors.primary, paddingVertical: 14, alignItems: 'center', marginTop: 12 },
  saveBtnLocked: { backgroundColor: '#0a0a0a', borderColor: Colors.border },
  saveTxt: { color: Colors.primary, fontFamily: Fonts.heading, fontSize: 14, letterSpacing: 3 },
  catRow: { gap: 6, paddingVertical: 12, paddingRight: 12 },
  catPill: { paddingHorizontal: 10, paddingVertical: 6, borderWidth: 1, borderColor: Colors.border, backgroundColor: '#000' },
  catActive: { borderColor: Colors.primary, backgroundColor: 'rgba(0,255,255,0.08)' },
  catTxt: { color: Colors.textMuted, fontFamily: Fonts.monoBold, fontSize: 10, letterSpacing: 1 },
  catTxtActive: { color: Colors.primary },
  libRow: { flexDirection: 'row', alignItems: 'center', paddingVertical: 10, paddingHorizontal: 10, borderBottomWidth: 1, borderBottomColor: Colors.border },
  libName: { color: Colors.textMain, fontFamily: Fonts.mono, fontSize: 13 },
  libMeta: { color: Colors.textMuted, fontFamily: Fonts.mono, fontSize: 10, marginTop: 2 },
});
