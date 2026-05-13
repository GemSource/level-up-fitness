import React, { useCallback, useState } from 'react';
import { View, Text, StyleSheet, ScrollView } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { useFocusEffect, useRouter } from 'expo-router';
import AsyncStorage from '@react-native-async-storage/async-storage';
import { Colors, Fonts, rankColor } from '../../src/theme';
import { SystemFrame } from '../../src/components/SystemFrame';
import { RankProgressCard } from '../../src/components/RankProgressCard';
import { getProgress, getRankProgress } from '../../src/api';

export default function Progress() {
  const router = useRouter();
  const [data, setData] = useState<any>(null);
  const [rankProg, setRankProg] = useState<any>(null);

  const load = async () => {
    const id = await AsyncStorage.getItem('profile_id');
    if (!id) { router.replace('/onboarding'); return; }
    const [d, rp] = await Promise.all([getProgress(id), getRankProgress(id)]);
    setData(d);
    setRankProg(rp);
  };

  useFocusEffect(useCallback(() => { load(); }, []));

  if (!data) return <SafeAreaView style={styles.safe}><Text style={styles.system}>[LOADING...]</Text></SafeAreaView>;

  const goalPct = Math.min(100, (data.current.total / data.goal_total) * 100);
  const rc = rankColor(data.rank);

  return (
    <SafeAreaView style={styles.safe}>
      <ScrollView contentContainerStyle={styles.scroll}>
        <Text style={styles.system}>[PROGRESS LOG]</Text>
        <Text style={styles.title}>HUNTER METRICS</Text>

        <Text style={styles.sectionLabel}>// RANK PROGRESS TRACKER</Text>
        {rankProg && <RankProgressCard data={rankProg} />}

        <SystemFrame style={styles.card} color={rc}>
          <Text style={styles.label}>// GOAL PROGRESS</Text>
          <Text style={[styles.goalNum, { color: rc }]}>
            {data.current.total} <Text style={styles.goalSep}>/</Text> {data.goal_total} KG
          </Text>
          <View style={styles.barBg}>
            <View style={[styles.barFill, { width: `${goalPct}%`, backgroundColor: rc, shadowColor: rc }]} />
          </View>
          <Text style={styles.goalPct}>{goalPct.toFixed(1)}% TO GOAL TOTAL</Text>
          <View style={styles.modeStrip}>
            <Text style={styles.modeBadge}>{(data.progression_mode || 'moderate').toUpperCase()}</Text>
            {data.estimated_weeks_to_goal && data.estimated_weeks_to_goal.max > 0 && (
              <Text style={styles.eta}>
                ETA: {data.estimated_weeks_to_goal.min}–{data.estimated_weeks_to_goal.max} WEEKS
              </Text>
            )}
          </View>
        </SystemFrame>

        <SystemFrame style={styles.card}>
          <Text style={styles.label}>// CURRENT MAXES</Text>
          <View style={styles.row}><Text style={styles.lift}>SQUAT</Text><Text style={styles.liftVal}>{data.current.squat} KG</Text></View>
          <View style={styles.row}><Text style={styles.lift}>BENCH</Text><Text style={styles.liftVal}>{data.current.bench} KG</Text></View>
          <View style={styles.row}><Text style={styles.lift}>DEADLIFT</Text><Text style={styles.liftVal}>{data.current.deadlift} KG</Text></View>
        </SystemFrame>

        <SystemFrame style={styles.card}>
          <Text style={styles.label}>// QUEST COMPLETION</Text>
          <Text style={styles.bigVal}>{data.completed_count} / {data.total_count}</Text>
          <Text style={styles.smallVal}>BLOCK QUESTS CLEARED</Text>
        </SystemFrame>

        <Text style={styles.sectionLabel}>// TOP SETS HISTORY</Text>
        {data.history.length === 0 ? (
          <SystemFrame style={styles.card}>
            <Text style={styles.empty}>No completed quests yet. Begin training to log history.</Text>
          </SystemFrame>
        ) : (
          data.history.slice().reverse().map((h: any, i: number) => (
            <View key={i} style={styles.histRow}>
              <Text style={styles.histDate}>{h.date ? new Date(h.date).toLocaleDateString() : '--'}</Text>
              <Text style={styles.histEx}>{h.exercise}</Text>
              <Text style={styles.histWeight}>{h.weight} × {h.reps}</Text>
            </View>
          ))
        )}
      </ScrollView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  safe: { flex: 1, backgroundColor: Colors.bg },
  scroll: { padding: 16, paddingBottom: 40 },
  system: { color: Colors.primary, fontFamily: Fonts.mono, fontSize: 10, letterSpacing: 3 },
  title: { color: Colors.textMain, fontFamily: Fonts.heading, fontSize: 22, letterSpacing: 1, marginTop: 2, marginBottom: 16 },
  card: { marginBottom: 12 },
  label: { color: Colors.primary, fontFamily: Fonts.monoBold, fontSize: 10, letterSpacing: 2, marginBottom: 8 },
  goalNum: { fontFamily: Fonts.heading, fontSize: 28, letterSpacing: 1, marginBottom: 8 },
  goalSep: { color: Colors.textDim, fontSize: 18 },
  barBg: { height: 8, backgroundColor: '#080808', borderWidth: 1, borderColor: Colors.borderGlow, overflow: 'hidden' },
  barFill: { height: '100%', shadowOpacity: 1, shadowRadius: 8, shadowOffset: { width: 0, height: 0 } },
  goalPct: { color: Colors.textMuted, fontFamily: Fonts.mono, fontSize: 10, letterSpacing: 2, marginTop: 6 },
  modeStrip: { flexDirection: 'row', alignItems: 'center', gap: 10, marginTop: 10 },
  modeBadge: { color: Colors.primary, fontFamily: Fonts.monoBold, fontSize: 9, letterSpacing: 2, paddingHorizontal: 6, paddingVertical: 3, borderWidth: 1, borderColor: Colors.borderGlow, backgroundColor: 'rgba(0,255,255,0.06)' },
  eta: { color: Colors.textMuted, fontFamily: Fonts.mono, fontSize: 10, letterSpacing: 1 },
  row: { flexDirection: 'row', justifyContent: 'space-between', paddingVertical: 6 },
  lift: { color: Colors.textMain, fontFamily: Fonts.heading, fontSize: 14, letterSpacing: 2 },
  liftVal: { color: Colors.primary, fontFamily: Fonts.monoBold, fontSize: 14, letterSpacing: 1 },
  bigVal: { color: Colors.primary, fontFamily: Fonts.heading, fontSize: 30, letterSpacing: 1 },
  smallVal: { color: Colors.textMuted, fontFamily: Fonts.mono, fontSize: 10, letterSpacing: 2 },
  sectionLabel: { color: Colors.primary, fontFamily: Fonts.monoBold, fontSize: 11, letterSpacing: 3, marginTop: 10, marginBottom: 10 },
  histRow: { flexDirection: 'row', justifyContent: 'space-between', paddingVertical: 10, borderBottomWidth: 1, borderBottomColor: Colors.border },
  histDate: { color: Colors.textMuted, fontFamily: Fonts.mono, fontSize: 11, width: 80 },
  histEx: { color: Colors.textMain, fontFamily: Fonts.mono, fontSize: 12, flex: 1 },
  histWeight: { color: Colors.primary, fontFamily: Fonts.monoBold, fontSize: 12 },
  empty: { color: Colors.textMuted, fontFamily: Fonts.mono, fontSize: 12, textAlign: 'center', padding: 12 },
});
