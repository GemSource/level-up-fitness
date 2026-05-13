import React, { useState } from 'react';
import {
  View, Text, StyleSheet, ScrollView, TextInput, TouchableOpacity,
  KeyboardAvoidingView, Platform, Alert,
} from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { useRouter } from 'expo-router';
import AsyncStorage from '@react-native-async-storage/async-storage';
import { Ionicons } from '@expo/vector-icons';
import { Colors, Fonts } from '../src/theme';
import { SystemFrame } from '../src/components/SystemFrame';
import { api } from '../src/api';

const ACTIVITIES = [
  { key: 'run', label: 'RUN', icon: 'walk-outline' as const },
  { key: 'bike', label: 'BIKE', icon: 'bicycle-outline' as const },
  { key: 'sprint', label: 'SPRINT', icon: 'flash-outline' as const },
];

const SPRINT_DISTANCES = [100, 200, 400];

export default function Cardio() {
  const router = useRouter();
  const [activity, setActivity] = useState<'run' | 'bike' | 'sprint'>('run');
  const [distanceKm, setDistanceKm] = useState('');
  const [durationMin, setDurationMin] = useState('');
  const [durationSec, setDurationSec] = useState('');
  const [sprintDistance, setSprintDistance] = useState(100);
  const [sprintTime, setSprintTime] = useState('');
  const [notes, setNotes] = useState('');
  const [submitting, setSubmitting] = useState(false);

  const submit = async () => {
    const pid = await AsyncStorage.getItem('profile_id');
    if (!pid) return;
    setSubmitting(true);
    try {
      const payload: any = { activity, notes };
      if (activity === 'sprint') {
        if (!sprintTime) { setSubmitting(false); return Alert.alert('[SYSTEM]', 'Enter sprint time.'); }
        payload.sprint_distance_m = sprintDistance;
        payload.sprint_time_sec = parseFloat(sprintTime);
      } else {
        if (!distanceKm) { setSubmitting(false); return Alert.alert('[SYSTEM]', 'Enter distance.'); }
        payload.distance_km = parseFloat(distanceKm);
        if (activity === 'run') {
          const total = (parseInt(durationMin) || 0) * 60 + (parseInt(durationSec) || 0);
          if (!total) { setSubmitting(false); return Alert.alert('[SYSTEM]', 'Enter duration for run.'); }
          payload.duration_sec = total;
        } else if (durationMin || durationSec) {
          payload.duration_sec = (parseInt(durationMin) || 0) * 60 + (parseInt(durationSec) || 0);
        }
      }
      const r = await api.post(`/profile/${pid}/cardio`, payload);
      const d = r.data;
      let msg = `+${d.xp_gained} XP`;
      if (d.achievement_xp > 0) msg += `\n+${d.achievement_xp} achievement XP`;
      msg += `\nLEVEL ${d.level}`;
      if (d.stats?.total_run_km) msg += `\nTotal Run: ${d.stats.total_run_km}km`;
      if (d.stats?.total_bike_km) msg += `\nTotal Bike: ${d.stats.total_bike_km}km`;
      if (d.new_achievements?.length) {
        msg += '\n\n[ACHIEVEMENTS UNLOCKED]\n' + d.new_achievements.map((a: any) => `★ ${a.name} (+${a.xp})`).join('\n');
      }
      Alert.alert('[CARDIO LOGGED]', msg, [
        { text: 'CONTINUE', onPress: () => router.replace('/(tabs)/dashboard') },
      ]);
    } catch (e: any) {
      Alert.alert('[SYSTEM ERROR]', e?.response?.data?.detail || e?.message || 'Failed');
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
            <Text style={styles.system}>[CARDIO LOG]</Text>
            <Text style={styles.title}>FIELD MISSION</Text>
          </View>
        </View>

        <ScrollView contentContainerStyle={styles.scroll} keyboardShouldPersistTaps="handled">
          <Text style={styles.label}>// SELECT ACTIVITY</Text>
          <View style={styles.activityRow}>
            {ACTIVITIES.map(a => (
              <TouchableOpacity
                key={a.key}
                testID={`activity-${a.key}`}
                onPress={() => setActivity(a.key as any)}
                style={[styles.actBtn, activity === a.key && styles.actBtnActive]}
              >
                <Ionicons name={a.icon} size={22} color={activity === a.key ? Colors.primary : Colors.textMuted} />
                <Text style={[styles.actTxt, activity === a.key && styles.actTxtActive]}>{a.label}</Text>
              </TouchableOpacity>
            ))}
          </View>

          {activity === 'sprint' ? (
            <SystemFrame style={styles.frame}>
              <Text style={styles.label}>// SPRINT DISTANCE</Text>
              <View style={styles.pillRow}>
                {SPRINT_DISTANCES.map(d => (
                  <TouchableOpacity
                    key={d}
                    testID={`sprint-${d}`}
                    onPress={() => setSprintDistance(d)}
                    style={[styles.pill, sprintDistance === d && styles.pillActive]}
                  >
                    <Text style={[styles.pillTxt, sprintDistance === d && styles.pillTxtActive]}>{d}m</Text>
                  </TouchableOpacity>
                ))}
              </View>
              <Text style={[styles.label, { marginTop: 16 }]}>// TIME (SECONDS)</Text>
              <TextInput
                testID="input-sprint-time"
                value={sprintTime}
                onChangeText={setSprintTime}
                placeholder="e.g. 18.5"
                placeholderTextColor={Colors.textDim}
                keyboardType="decimal-pad"
                style={styles.input}
              />
            </SystemFrame>
          ) : (
            <SystemFrame style={styles.frame}>
              <Text style={styles.label}>// DISTANCE (KM)</Text>
              <TextInput
                testID="input-distance"
                value={distanceKm}
                onChangeText={setDistanceKm}
                placeholder="5.0"
                placeholderTextColor={Colors.textDim}
                keyboardType="decimal-pad"
                style={styles.input}
              />
              <Text style={[styles.label, { marginTop: 16 }]}>
                // DURATION {activity === 'run' ? '(REQUIRED FOR PACE)' : '(OPTIONAL)'}
              </Text>
              <View style={styles.durRow}>
                <View style={{ flex: 1 }}>
                  <TextInput
                    testID="input-min"
                    value={durationMin}
                    onChangeText={setDurationMin}
                    placeholder="MIN"
                    placeholderTextColor={Colors.textDim}
                    keyboardType="number-pad"
                    style={styles.input}
                  />
                </View>
                <Text style={styles.colon}>:</Text>
                <View style={{ flex: 1 }}>
                  <TextInput
                    testID="input-sec"
                    value={durationSec}
                    onChangeText={setDurationSec}
                    placeholder="SEC"
                    placeholderTextColor={Colors.textDim}
                    keyboardType="number-pad"
                    style={styles.input}
                  />
                </View>
              </View>
            </SystemFrame>
          )}

          <SystemFrame style={styles.frame}>
            <Text style={styles.label}>// NOTES</Text>
            <TextInput
              testID="input-notes"
              value={notes}
              onChangeText={setNotes}
              multiline
              placeholder="Conditions, perceived effort..."
              placeholderTextColor={Colors.textDim}
              style={[styles.input, { minHeight: 60, textAlignVertical: 'top' }]}
            />
          </SystemFrame>

          <TouchableOpacity
            testID="btn-submit-cardio"
            style={styles.submit}
            onPress={submit}
            disabled={submitting}
          >
            <Text style={styles.submitTxt}>{submitting ? 'TRANSMITTING...' : 'LOG MISSION ⚡'}</Text>
          </TouchableOpacity>
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
  label: { color: Colors.primary, fontFamily: Fonts.monoBold, fontSize: 11, letterSpacing: 2, marginBottom: 8 },
  activityRow: { flexDirection: 'row', gap: 8, marginBottom: 16 },
  actBtn: { flex: 1, paddingVertical: 16, alignItems: 'center', gap: 6, borderWidth: 1, borderColor: Colors.border, backgroundColor: '#000' },
  actBtnActive: { borderColor: Colors.primary, backgroundColor: 'rgba(0,255,255,0.08)', shadowColor: Colors.primary, shadowOpacity: 0.5, shadowRadius: 8 },
  actTxt: { color: Colors.textMuted, fontFamily: Fonts.monoBold, fontSize: 11, letterSpacing: 2 },
  actTxtActive: { color: Colors.primary },
  frame: { marginBottom: 12 },
  input: { backgroundColor: '#000', borderWidth: 1, borderColor: Colors.borderGlow, color: Colors.textMain, fontFamily: Fonts.mono, fontSize: 16, padding: 12 },
  durRow: { flexDirection: 'row', alignItems: 'center', gap: 6 },
  colon: { color: Colors.primary, fontFamily: Fonts.monoBold, fontSize: 20 },
  pillRow: { flexDirection: 'row', gap: 8 },
  pill: { flex: 1, paddingVertical: 12, alignItems: 'center', borderWidth: 1, borderColor: Colors.border, backgroundColor: '#000' },
  pillActive: { borderColor: Colors.primary, backgroundColor: 'rgba(0,255,255,0.08)' },
  pillTxt: { color: Colors.textMuted, fontFamily: Fonts.monoBold, fontSize: 12, letterSpacing: 1 },
  pillTxtActive: { color: Colors.primary },
  submit: { backgroundColor: 'rgba(0,255,255,0.1)', borderWidth: 1, borderColor: Colors.primary, paddingVertical: 16, alignItems: 'center', marginTop: 8, shadowColor: Colors.primary, shadowOpacity: 0.5, shadowRadius: 12 },
  submitTxt: { color: Colors.primary, fontFamily: Fonts.heading, fontSize: 16, letterSpacing: 3 },
});
