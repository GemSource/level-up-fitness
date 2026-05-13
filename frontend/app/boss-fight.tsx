import React, { useEffect, useState } from 'react';
import {
  View, Text, StyleSheet, ScrollView, TextInput, TouchableOpacity,
  KeyboardAvoidingView, Platform, Alert, Animated,
} from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { useRouter } from 'expo-router';
import AsyncStorage from '@react-native-async-storage/async-storage';
import { Ionicons } from '@expo/vector-icons';
import { Colors, Fonts, rankColor } from '../src/theme';
import { SystemFrame } from '../src/components/SystemFrame';
import { RankBadge } from '../src/components/RankBadge';
import { bossFight } from '../src/api';

export default function BossFight() {
  const router = useRouter();
  const [squat, setSquat] = useState('');
  const [bench, setBench] = useState('');
  const [deadlift, setDeadlift] = useState('');
  const [result, setResult] = useState<any>(null);
  const [submitting, setSubmitting] = useState(false);
  const pulse = useState(new Animated.Value(1))[0];

  useEffect(() => {
    Animated.loop(
      Animated.sequence([
        Animated.timing(pulse, { toValue: 1.05, duration: 800, useNativeDriver: true }),
        Animated.timing(pulse, { toValue: 1, duration: 800, useNativeDriver: true }),
      ])
    ).start();
  }, []);

  const submit = async () => {
    const pid = await AsyncStorage.getItem('profile_id');
    if (!pid) return;
    if (!squat || !bench || !deadlift) {
      return Alert.alert('[SYSTEM]', 'Enter all three lifts.');
    }
    setSubmitting(true);
    try {
      const r = await bossFight(pid, {
        squat_max: parseFloat(squat),
        bench_max: parseFloat(bench),
        deadlift_max: parseFloat(deadlift),
      });
      setResult(r);
    } catch (e: any) {
      Alert.alert('[SYSTEM ERROR]', e?.message || 'Failed');
    } finally {
      setSubmitting(false);
    }
  };

  if (result) {
    const rc = rankColor(result.new_rank);
    return (
      <SafeAreaView style={styles.safe}>
        <ScrollView contentContainerStyle={styles.resultScroll}>
          <Text style={[styles.victory, { color: result.rank_up ? Colors.questComplete : Colors.primary }]}>
            {result.rank_up ? '[RANK UP]' : '[BOSS DEFEATED]'}
          </Text>
          <Animated.View style={{ transform: [{ scale: pulse }], marginVertical: 30 }}>
            <RankBadge rank={result.new_rank} size={150} />
          </Animated.View>
          {result.rank_up && (
            <Text style={[styles.rankUpTxt, { color: rc }]}>
              {result.old_rank} → {result.new_rank}
            </Text>
          )}
          <SystemFrame style={styles.resCard} color={rc}>
            <View style={styles.resRow}><Text style={styles.resLbl}>NEW TOTAL</Text><Text style={[styles.resVal, { color: rc }]}>{result.new_total} KG</Text></View>
            <View style={styles.resRow}><Text style={styles.resLbl}>GROWTH</Text><Text style={styles.resVal}>+{(result.new_total - result.old_total).toFixed(1)} KG</Text></View>
            <View style={styles.resRow}><Text style={styles.resLbl}>XP REWARD</Text><Text style={styles.resVal}>+{result.xp_reward}</Text></View>
          </SystemFrame>
          {result.new_achievements?.length > 0 && (
            <View style={{ marginTop: 20 }}>
              <Text style={styles.system}>[ACHIEVEMENTS]</Text>
              {result.new_achievements.map((a: any) => (
                <Text key={a.key} style={styles.achLine}>★ {a.name}</Text>
              ))}
            </View>
          )}
          <Text style={styles.continueHint}>// A new 6-week block has been forged from your power.</Text>
          <TouchableOpacity testID="btn-continue" style={styles.continueBtn} onPress={() => router.replace('/(tabs)/dashboard')}>
            <Text style={styles.continueTxt}>RETURN TO STATUS</Text>
          </TouchableOpacity>
        </ScrollView>
      </SafeAreaView>
    );
  }

  return (
    <SafeAreaView style={styles.safe}>
      <KeyboardAvoidingView style={{ flex: 1 }} behavior={Platform.OS === 'ios' ? 'padding' : undefined}>
        <ScrollView contentContainerStyle={styles.scroll}>
          <View style={styles.header}>
            <TouchableOpacity onPress={() => router.back()} testID="btn-back">
              <Ionicons name="chevron-back" size={24} color={Colors.danger} />
            </TouchableOpacity>
          </View>
          <Animated.View style={{ alignItems: 'center', transform: [{ scale: pulse }] }}>
            <Text style={styles.warn}>⚠ [BOSS FIGHT INITIATED] ⚠</Text>
            <Text style={styles.title}>MAX TEST PROTOCOL</Text>
            <Text style={styles.sub}>// LOG YOUR NEW 1-REP MAX FOR EACH LIFT</Text>
          </Animated.View>

          <SystemFrame style={styles.frame} color={Colors.danger}>
            <View style={styles.liftRow}>
              <Text style={styles.liftLbl}>SQUAT</Text>
              <TextInput
                testID="boss-squat"
                value={squat}
                onChangeText={setSquat}
                placeholder="0"
                placeholderTextColor={Colors.textDim}
                keyboardType="decimal-pad"
                style={styles.input}
              />
            </View>
            <View style={styles.liftRow}>
              <Text style={styles.liftLbl}>BENCH</Text>
              <TextInput
                testID="boss-bench"
                value={bench}
                onChangeText={setBench}
                placeholder="0"
                placeholderTextColor={Colors.textDim}
                keyboardType="decimal-pad"
                style={styles.input}
              />
            </View>
            <View style={styles.liftRow}>
              <Text style={styles.liftLbl}>DEADLIFT</Text>
              <TextInput
                testID="boss-deadlift"
                value={deadlift}
                onChangeText={setDeadlift}
                placeholder="0"
                placeholderTextColor={Colors.textDim}
                keyboardType="decimal-pad"
                style={styles.input}
              />
            </View>
          </SystemFrame>

          <TouchableOpacity
            testID="btn-engage-boss"
            style={styles.engageBtn}
            onPress={submit}
            disabled={submitting}
          >
            <Text style={styles.engageTxt}>{submitting ? 'BATTLING...' : 'ENGAGE BOSS ⚔'}</Text>
          </TouchableOpacity>
        </ScrollView>
      </KeyboardAvoidingView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  safe: { flex: 1, backgroundColor: Colors.bg },
  scroll: { padding: 20, paddingBottom: 40 },
  header: { marginBottom: 10 },
  warn: { color: Colors.danger, fontFamily: Fonts.monoBold, fontSize: 12, letterSpacing: 3, textShadowColor: Colors.dangerGlow, textShadowRadius: 12, marginTop: 20 },
  title: { color: Colors.textMain, fontFamily: Fonts.heading, fontSize: 28, letterSpacing: 2, marginTop: 12, textShadowColor: Colors.dangerGlow, textShadowRadius: 12 },
  sub: { color: Colors.textMuted, fontFamily: Fonts.mono, fontSize: 10, letterSpacing: 2, marginTop: 8, marginBottom: 30 },
  frame: { marginBottom: 24 },
  liftRow: { flexDirection: 'row', alignItems: 'center', paddingVertical: 8 },
  liftLbl: { color: Colors.textMain, fontFamily: Fonts.heading, fontSize: 16, letterSpacing: 2, width: 110 },
  input: { flex: 1, backgroundColor: '#000', borderWidth: 1, borderColor: 'rgba(255,0,85,0.4)', color: Colors.danger, fontFamily: Fonts.monoBold, fontSize: 20, padding: 12, textAlign: 'right' },
  engageBtn: { backgroundColor: 'rgba(255,0,85,0.1)', borderWidth: 1, borderColor: Colors.danger, paddingVertical: 18, alignItems: 'center', shadowColor: Colors.danger, shadowOpacity: 0.6, shadowRadius: 14 },
  engageTxt: { color: Colors.danger, fontFamily: Fonts.heading, fontSize: 18, letterSpacing: 4 },
  resultScroll: { padding: 20, alignItems: 'center', paddingBottom: 60 },
  victory: { fontFamily: Fonts.heading, fontSize: 24, letterSpacing: 4, marginTop: 30, textShadowColor: Colors.primaryGlow, textShadowRadius: 16 },
  rankUpTxt: { fontFamily: Fonts.heading, fontSize: 36, letterSpacing: 6, textShadowRadius: 20 },
  resCard: { width: '100%', marginTop: 24 },
  resRow: { flexDirection: 'row', justifyContent: 'space-between', paddingVertical: 8, borderBottomWidth: 1, borderBottomColor: Colors.border },
  resLbl: { color: Colors.textMuted, fontFamily: Fonts.mono, fontSize: 11, letterSpacing: 2 },
  resVal: { color: Colors.textMain, fontFamily: Fonts.monoBold, fontSize: 16 },
  system: { color: Colors.primary, fontFamily: Fonts.mono, fontSize: 10, letterSpacing: 2, marginBottom: 6 },
  achLine: { color: Colors.questComplete, fontFamily: Fonts.monoBold, fontSize: 13, letterSpacing: 1, marginVertical: 2 },
  continueHint: { color: Colors.textMuted, fontFamily: Fonts.mono, fontSize: 10, letterSpacing: 1, marginTop: 24, textAlign: 'center' },
  continueBtn: { marginTop: 16, paddingVertical: 14, paddingHorizontal: 30, borderWidth: 1, borderColor: Colors.primary, backgroundColor: 'rgba(0,255,255,0.08)' },
  continueTxt: { color: Colors.primary, fontFamily: Fonts.heading, fontSize: 14, letterSpacing: 3 },
});
