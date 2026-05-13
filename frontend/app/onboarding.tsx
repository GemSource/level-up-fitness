import React, { useState } from 'react';
import {
  View, Text, TextInput, TouchableOpacity, StyleSheet, ScrollView,
  KeyboardAvoidingView, Platform, Alert,
} from 'react-native';
import AsyncStorage from '@react-native-async-storage/async-storage';
import { useRouter } from 'expo-router';
import { SafeAreaView } from 'react-native-safe-area-context';
import { Colors, Fonts } from '../src/theme';
import { SystemFrame } from '../src/components/SystemFrame';
import { createProfile } from '../src/api';

const EXPERIENCE = ['Beginner', 'Intermediate', 'Advanced'];

export default function Onboarding() {
  const router = useRouter();
  const [step, setStep] = useState(0);
  const [loading, setLoading] = useState(false);
  const [form, setForm] = useState({
    name: '',
    bodyweight: '',
    experience: 'Intermediate',
    squat_max: '',
    bench_max: '',
    deadlift_max: '',
    training_days: '4',
    goal_total: '1000',
  });

  const update = (k: string, v: string) => setForm({ ...form, [k]: v });

  const next = () => {
    if (step === 0 && !form.name.trim()) return Alert.alert('[SYSTEM]', 'Identify yourself, Hunter.');
    if (step === 1 && !form.bodyweight) return Alert.alert('[SYSTEM]', 'Bodyweight required.');
    if (step === 2 && (!form.squat_max || !form.bench_max || !form.deadlift_max)) {
      return Alert.alert('[SYSTEM]', 'Enter all three lift maxes.');
    }
    setStep(step + 1);
  };

  const submit = async () => {
    setLoading(true);
    try {
      const payload = {
        name: form.name.trim(),
        bodyweight: parseFloat(form.bodyweight),
        experience: form.experience,
        squat_max: parseFloat(form.squat_max),
        bench_max: parseFloat(form.bench_max),
        deadlift_max: parseFloat(form.deadlift_max),
        training_days: parseInt(form.training_days),
        goal_total: parseFloat(form.goal_total),
      };
      const profile = await createProfile(payload);
      await AsyncStorage.setItem('profile_id', profile.id);
      router.replace('/(tabs)/dashboard');
    } catch (e: any) {
      Alert.alert('[SYSTEM ERROR]', e?.message || 'Connection failed.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <SafeAreaView style={styles.safe}>
      <KeyboardAvoidingView
        style={{ flex: 1 }}
        behavior={Platform.OS === 'ios' ? 'padding' : undefined}
      >
        <ScrollView contentContainerStyle={styles.scroll} keyboardShouldPersistTaps="handled">
          <Text style={styles.system}>[SYSTEM AWAKENING]</Text>
          <Text style={styles.title}>HUNTER STRENGTH SYSTEM</Text>
          <Text style={styles.subtitle}>// REGISTRATION PROTOCOL</Text>

          <View style={styles.stepRow}>
            {[0,1,2,3].map(i => (
              <View key={i} style={[styles.stepDot, step >= i && styles.stepDotActive]} />
            ))}
          </View>

          {step === 0 && (
            <SystemFrame style={styles.frame}>
              <Text style={styles.label}>// HUNTER NAME</Text>
              <TextInput
                testID="input-name"
                value={form.name}
                onChangeText={(v) => update('name', v)}
                placeholder="ENTER CALLSIGN"
                placeholderTextColor={Colors.textDim}
                style={styles.input}
              />
            </SystemFrame>
          )}

          {step === 1 && (
            <SystemFrame style={styles.frame}>
              <Text style={styles.label}>// BODYWEIGHT (KG)</Text>
              <TextInput
                testID="input-bodyweight"
                value={form.bodyweight}
                onChangeText={(v) => update('bodyweight', v)}
                placeholder="75"
                placeholderTextColor={Colors.textDim}
                keyboardType="decimal-pad"
                style={styles.input}
              />
              <Text style={[styles.label, { marginTop: 16 }]}>// EXPERIENCE TIER</Text>
              <View style={styles.pillRow}>
                {EXPERIENCE.map(e => (
                  <TouchableOpacity
                    key={e}
                    testID={`experience-${e}`}
                    onPress={() => update('experience', e)}
                    style={[styles.pill, form.experience === e && styles.pillActive]}
                  >
                    <Text style={[styles.pillText, form.experience === e && styles.pillTextActive]}>{e}</Text>
                  </TouchableOpacity>
                ))}
              </View>
            </SystemFrame>
          )}

          {step === 2 && (
            <SystemFrame style={styles.frame}>
              <Text style={styles.label}>// CURRENT MAX LIFTS (KG)</Text>
              <View style={styles.liftRow}>
                <Text style={styles.liftLabel}>SQUAT</Text>
                <TextInput
                  testID="input-squat"
                  value={form.squat_max}
                  onChangeText={(v) => update('squat_max', v)}
                  placeholder="0"
                  placeholderTextColor={Colors.textDim}
                  keyboardType="decimal-pad"
                  style={styles.inputLift}
                />
              </View>
              <View style={styles.liftRow}>
                <Text style={styles.liftLabel}>BENCH</Text>
                <TextInput
                  testID="input-bench"
                  value={form.bench_max}
                  onChangeText={(v) => update('bench_max', v)}
                  placeholder="0"
                  placeholderTextColor={Colors.textDim}
                  keyboardType="decimal-pad"
                  style={styles.inputLift}
                />
              </View>
              <View style={styles.liftRow}>
                <Text style={styles.liftLabel}>DEADLIFT</Text>
                <TextInput
                  testID="input-deadlift"
                  value={form.deadlift_max}
                  onChangeText={(v) => update('deadlift_max', v)}
                  placeholder="0"
                  placeholderTextColor={Colors.textDim}
                  keyboardType="decimal-pad"
                  style={styles.inputLift}
                />
              </View>
            </SystemFrame>
          )}

          {step === 3 && (
            <SystemFrame style={styles.frame}>
              <Text style={styles.label}>// TRAINING DAYS / WEEK</Text>
              <View style={styles.pillRow}>
                {['3','4','5','6'].map(d => (
                  <TouchableOpacity
                    key={d}
                    testID={`days-${d}`}
                    onPress={() => update('training_days', d)}
                    style={[styles.pill, form.training_days === d && styles.pillActive]}
                  >
                    <Text style={[styles.pillText, form.training_days === d && styles.pillTextActive]}>{d}</Text>
                  </TouchableOpacity>
                ))}
              </View>
              <Text style={[styles.label, { marginTop: 16 }]}>// GOAL TOTAL (KG)</Text>
              <TextInput
                testID="input-goal"
                value={form.goal_total}
                onChangeText={(v) => update('goal_total', v)}
                placeholder="1000"
                placeholderTextColor={Colors.textDim}
                keyboardType="decimal-pad"
                style={styles.input}
              />
            </SystemFrame>
          )}

          <View style={styles.btnRow}>
            {step > 0 && (
              <TouchableOpacity
                testID="btn-back"
                style={[styles.btn, styles.btnGhost]}
                onPress={() => setStep(step - 1)}
              >
                <Text style={styles.btnGhostText}>‹ BACK</Text>
              </TouchableOpacity>
            )}
            {step < 3 ? (
              <TouchableOpacity testID="btn-next" style={styles.btn} onPress={next}>
                <Text style={styles.btnText}>NEXT ›</Text>
              </TouchableOpacity>
            ) : (
              <TouchableOpacity
                testID="btn-begin"
                style={styles.btn}
                onPress={submit}
                disabled={loading}
              >
                <Text style={styles.btnText}>{loading ? 'AWAKENING...' : 'AWAKEN ⚔'}</Text>
              </TouchableOpacity>
            )}
          </View>
        </ScrollView>
      </KeyboardAvoidingView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  safe: { flex: 1, backgroundColor: Colors.bg },
  scroll: { padding: 20, paddingBottom: 60 },
  system: { color: Colors.primary, fontFamily: Fonts.mono, fontSize: 11, letterSpacing: 3, marginTop: 20 },
  title: { color: Colors.textMain, fontFamily: Fonts.heading, fontSize: 28, letterSpacing: 1, marginTop: 6, textShadowColor: Colors.primaryGlow, textShadowRadius: 12 },
  subtitle: { color: Colors.textMuted, fontFamily: Fonts.mono, fontSize: 10, letterSpacing: 2, marginTop: 4, marginBottom: 24 },
  stepRow: { flexDirection: 'row', gap: 6, marginBottom: 20 },
  stepDot: { width: 30, height: 3, backgroundColor: Colors.border },
  stepDotActive: { backgroundColor: Colors.primary, shadowColor: Colors.primary, shadowOpacity: 1, shadowRadius: 6 },
  frame: { marginBottom: 24 },
  label: { color: Colors.primary, fontFamily: Fonts.monoBold, fontSize: 11, letterSpacing: 2, marginBottom: 10 },
  input: {
    backgroundColor: '#000',
    borderWidth: 1,
    borderColor: Colors.borderGlow,
    color: Colors.textMain,
    fontFamily: Fonts.mono,
    fontSize: 18,
    padding: 14,
    letterSpacing: 1,
  },
  pillRow: { flexDirection: 'row', gap: 8, flexWrap: 'wrap' },
  pill: {
    flex: 1, minWidth: 60, paddingVertical: 12, paddingHorizontal: 8,
    borderWidth: 1, borderColor: Colors.border, backgroundColor: '#000', alignItems: 'center',
  },
  pillActive: { borderColor: Colors.primary, backgroundColor: 'rgba(0,255,255,0.08)', shadowColor: Colors.primary, shadowOpacity: 0.4, shadowRadius: 8 },
  pillText: { color: Colors.textMuted, fontFamily: Fonts.monoBold, letterSpacing: 1, fontSize: 12 },
  pillTextActive: { color: Colors.primary },
  liftRow: { flexDirection: 'row', alignItems: 'center', marginBottom: 12 },
  liftLabel: { color: Colors.textMain, fontFamily: Fonts.heading, fontSize: 16, letterSpacing: 2, width: 100 },
  inputLift: {
    flex: 1, backgroundColor: '#000', borderWidth: 1, borderColor: Colors.borderGlow,
    color: Colors.primary, fontFamily: Fonts.monoBold, fontSize: 18, padding: 12, textAlign: 'right',
  },
  btnRow: { flexDirection: 'row', gap: 12, marginTop: 12 },
  btn: {
    flex: 1, paddingVertical: 16, alignItems: 'center', backgroundColor: 'rgba(0,255,255,0.08)',
    borderWidth: 1, borderColor: Colors.primary, shadowColor: Colors.primary, shadowOpacity: 0.5, shadowRadius: 10,
  },
  btnText: { color: Colors.primary, fontFamily: Fonts.heading, fontSize: 16, letterSpacing: 3 },
  btnGhost: { backgroundColor: 'transparent', borderColor: Colors.border, shadowOpacity: 0, flex: 0.5 },
  btnGhostText: { color: Colors.textMuted, fontFamily: Fonts.heading, fontSize: 14, letterSpacing: 2 },
});
