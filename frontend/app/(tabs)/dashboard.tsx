import React, { useCallback, useState } from 'react';
import { View, Text, StyleSheet, ScrollView, TouchableOpacity, RefreshControl, Alert } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { useFocusEffect, useRouter } from 'expo-router';
import AsyncStorage from '@react-native-async-storage/async-storage';
import { Ionicons } from '@expo/vector-icons';
import { Colors, Fonts, rankColor } from '../../src/theme';
import { SystemFrame } from '../../src/components/SystemFrame';
import { RankBadge } from '../../src/components/RankBadge';
import { XPBar } from '../../src/components/XPBar';
import { getDashboard } from '../../src/api';

export default function Dashboard() {
  const router = useRouter();
  const [data, setData] = useState<any>(null);
  const [refreshing, setRefreshing] = useState(false);

  const load = async () => {
    const id = await AsyncStorage.getItem('profile_id');
    if (!id) { router.replace('/onboarding'); return; }
    try {
      const d = await getDashboard(id);
      setData(d);
    } catch (e: any) {
      if (e?.response?.status === 404) {
        await AsyncStorage.removeItem('profile_id');
        router.replace('/onboarding');
        return;
      }
      console.log('dash err', e?.message);
    }
  };

  useFocusEffect(useCallback(() => { load(); }, []));

  const onRefresh = async () => {
    setRefreshing(true);
    await load();
    setRefreshing(false);
  };

  const reset = async () => {
    Alert.alert('[SYSTEM]', 'Reset hunter profile?', [
      { text: 'CANCEL', style: 'cancel' },
      { text: 'RESET', style: 'destructive', onPress: async () => {
        await AsyncStorage.removeItem('profile_id');
        router.replace('/onboarding');
      }},
    ]);
  };

  if (!data) {
    return <SafeAreaView style={styles.safe}><Text style={styles.system}>[SYSTEM CONNECTING...]</Text></SafeAreaView>;
  }

  const p = data.profile;
  const quest = data.today_quest;
  const nr = data.next_rank;
  const rc = rankColor(p.rank);

  return (
    <SafeAreaView style={styles.safe}>
      <ScrollView
        contentContainerStyle={styles.scroll}
        refreshControl={<RefreshControl refreshing={refreshing} onRefresh={onRefresh} tintColor={Colors.primary} />}
      >
        <View style={styles.headerRow}>
          <View>
            <Text style={styles.system}>[STATUS WINDOW]</Text>
            <Text style={styles.title}>{p.name.toUpperCase()}</Text>
          </View>
          <TouchableOpacity testID="btn-coach" onPress={() => router.push('/ai-coach')}>
            <Ionicons name="planet-outline" size={28} color={Colors.primary} />
          </TouchableOpacity>
        </View>

        <SystemFrame style={styles.heroFrame} color={rc}>
          <View style={styles.heroRow}>
            <RankBadge rank={p.rank} size={92} />
            <View style={{ flex: 1, marginLeft: 18 }}>
              <Text style={[styles.heroLabel, { color: rc }]}>RANK</Text>
              <Text style={[styles.heroRank, { color: rc, textShadowColor: rc }]}>{p.rank}</Text>
              <Text style={styles.heroTotal}>{p.total} <Text style={styles.heroUnit}>KG TOTAL</Text></Text>
            </View>
          </View>
          <View style={styles.xpWrap}>
            <XPBar current={p.xp} max={data.xp_to_next_level} level={p.level} />
          </View>
          {nr.rank !== p.rank && (
            <View style={styles.nextRow}>
              <Text style={styles.nextLabel}>// NEXT RANK</Text>
              <Text style={styles.nextValue}>{nr.kg_to_reach.toFixed(1)} KG → {nr.rank}</Text>
            </View>
          )}
          <View style={styles.modeRow}>
            <Text style={styles.modeBadge}>{(p.progression_mode || 'moderate').toUpperCase()} MODE</Text>
            {p.estimated_weeks_to_goal && p.estimated_weeks_to_goal.max > 0 && (
              <Text style={styles.etaText}>
                ETA TO GOAL: {p.estimated_weeks_to_goal.min}-{p.estimated_weeks_to_goal.max} WEEKS
              </Text>
            )}
          </View>
        </SystemFrame>

        <View style={styles.statsRow}>
          <SystemFrame style={styles.statCard}>
            <Text style={styles.statLabel}>SQUAT</Text>
            <Text style={styles.statValue}>{p.squat_max}</Text>
            <Text style={styles.statUnit}>KG</Text>
          </SystemFrame>
          <SystemFrame style={styles.statCard}>
            <Text style={styles.statLabel}>BENCH</Text>
            <Text style={styles.statValue}>{p.bench_max}</Text>
            <Text style={styles.statUnit}>KG</Text>
          </SystemFrame>
          <SystemFrame style={styles.statCard}>
            <Text style={styles.statLabel}>DEAD</Text>
            <Text style={styles.statValue}>{p.deadlift_max}</Text>
            <Text style={styles.statUnit}>KG</Text>
          </SystemFrame>
        </View>

        <View style={styles.miniRow}>
          <View style={styles.miniCard}>
            <Ionicons name="flame" size={16} color={Colors.danger} />
            <Text style={styles.miniText}>{p.streak} DAY STREAK</Text>
          </View>
          <View style={styles.miniCard}>
            <Ionicons name="trophy" size={16} color={Colors.primary} />
            <Text style={styles.miniText}>{(p.achievements || []).length} TROPHIES</Text>
          </View>
        </View>

        <Text style={styles.sectionLabel}>// TODAY'S QUEST</Text>
        {quest ? (
          <TouchableOpacity testID="btn-today-quest" onPress={() => router.push(`/workout/${quest.id}`)}>
            <SystemFrame style={styles.questCard}>
              <View style={styles.questHeader}>
                <Text style={styles.questBadge}>{quest.week_label} · WK {quest.week}</Text>
                <Ionicons name="chevron-forward" size={20} color={Colors.primary} />
              </View>
              <Text style={styles.questTitle}>{quest.day_type.replace('_', ' ')}</Text>
              {quest.exercises.slice(0, 3).map((ex: any, i: number) => (
                <View key={i} style={styles.exRow}>
                  <Text style={[styles.exName, ex.is_main && { color: Colors.primary }]}>
                    {ex.is_main ? '★ ' : '· '}{ex.name}
                  </Text>
                  <Text style={styles.exDetail}>{ex.sets}×{ex.reps} @ {ex.weight}kg</Text>
                </View>
              ))}
            </SystemFrame>
          </TouchableOpacity>
        ) : (
          <SystemFrame style={styles.questCard}>
            <Text style={styles.questTitle}>BLOCK COMPLETE</Text>
            <Text style={styles.exDetail}>Trigger the Boss Fight to test new maxes.</Text>
          </SystemFrame>
        )}

        <View style={{ height: 16 }} />
        <TouchableOpacity
          testID="btn-boss-fight"
          style={[styles.bigBtn, styles.bossBtn]}
          onPress={() => router.push('/boss-fight')}
        >
          <Ionicons name="skull-outline" size={20} color={Colors.danger} />
          <Text style={styles.bossText}>BOSS FIGHT // MAX TEST</Text>
        </TouchableOpacity>

        <TouchableOpacity testID="btn-reset" onPress={reset} style={styles.resetBtn}>
          <Text style={styles.resetText}>RESET HUNTER</Text>
        </TouchableOpacity>
      </ScrollView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  safe: { flex: 1, backgroundColor: Colors.bg },
  scroll: { padding: 16, paddingBottom: 40 },
  headerRow: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16 },
  system: { color: Colors.primary, fontFamily: Fonts.mono, fontSize: 10, letterSpacing: 3 },
  title: { color: Colors.textMain, fontFamily: Fonts.heading, fontSize: 22, letterSpacing: 1, marginTop: 2 },
  heroFrame: { marginBottom: 16 },
  heroRow: { flexDirection: 'row', alignItems: 'center', marginBottom: 16 },
  heroLabel: { fontFamily: Fonts.monoBold, fontSize: 10, letterSpacing: 3 },
  heroRank: { fontFamily: Fonts.heading, fontSize: 56, letterSpacing: 2, lineHeight: 60, textShadowRadius: 16 },
  heroTotal: { color: Colors.textMain, fontFamily: Fonts.monoBold, fontSize: 22, letterSpacing: 1, marginTop: 4 },
  heroUnit: { color: Colors.textMuted, fontSize: 11, letterSpacing: 2, fontFamily: Fonts.mono },
  xpWrap: { marginBottom: 8 },
  nextRow: { flexDirection: 'row', justifyContent: 'space-between', marginTop: 10, paddingTop: 10, borderTopWidth: 1, borderTopColor: Colors.border },
  nextLabel: { color: Colors.textMuted, fontFamily: Fonts.mono, fontSize: 10, letterSpacing: 2 },
  nextValue: { color: Colors.primary, fontFamily: Fonts.monoBold, fontSize: 11, letterSpacing: 1 },
  statsRow: { flexDirection: 'row', gap: 8, marginBottom: 12 },
  statCard: { flex: 1, padding: 12, alignItems: 'center' },
  statLabel: { color: Colors.textMuted, fontFamily: Fonts.mono, fontSize: 9, letterSpacing: 2 },
  statValue: { color: Colors.primary, fontFamily: Fonts.monoBold, fontSize: 22, marginTop: 4 },
  statUnit: { color: Colors.textDim, fontFamily: Fonts.mono, fontSize: 9, letterSpacing: 1 },
  miniRow: { flexDirection: 'row', gap: 10, marginBottom: 20 },
  miniCard: { flexDirection: 'row', alignItems: 'center', gap: 6, paddingHorizontal: 10, paddingVertical: 6, borderWidth: 1, borderColor: Colors.border, backgroundColor: Colors.surface },
  miniText: { color: Colors.textMain, fontFamily: Fonts.mono, fontSize: 10, letterSpacing: 1 },
  sectionLabel: { color: Colors.primary, fontFamily: Fonts.monoBold, fontSize: 11, letterSpacing: 3, marginBottom: 10, marginTop: 8 },
  questCard: { borderColor: 'rgba(0,255,255,0.4)' },
  questHeader: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center' },
  questBadge: { color: Colors.primary, fontFamily: Fonts.monoBold, fontSize: 10, letterSpacing: 2, backgroundColor: 'rgba(0,255,255,0.08)', paddingHorizontal: 8, paddingVertical: 3 },
  questTitle: { color: Colors.textMain, fontFamily: Fonts.heading, fontSize: 22, letterSpacing: 2, marginTop: 8, marginBottom: 10 },
  exRow: { flexDirection: 'row', justifyContent: 'space-between', paddingVertical: 4 },
  exName: { color: Colors.textMain, fontFamily: Fonts.mono, fontSize: 13 },
  exDetail: { color: Colors.textMuted, fontFamily: Fonts.mono, fontSize: 12 },
  bigBtn: { flexDirection: 'row', alignItems: 'center', justifyContent: 'center', gap: 10, paddingVertical: 16, borderWidth: 1 },
  bossBtn: { backgroundColor: 'rgba(255,0,85,0.06)', borderColor: Colors.danger, shadowColor: Colors.danger, shadowOpacity: 0.5, shadowRadius: 10 },
  bossText: { color: Colors.danger, fontFamily: Fonts.heading, fontSize: 14, letterSpacing: 3 },
  resetBtn: { marginTop: 24, alignItems: 'center', padding: 10 },
  resetText: { color: Colors.textDim, fontFamily: Fonts.mono, fontSize: 10, letterSpacing: 2 },
  modeRow: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', marginTop: 8 },
  modeBadge: { color: Colors.primary, fontFamily: Fonts.monoBold, fontSize: 9, letterSpacing: 2, paddingHorizontal: 6, paddingVertical: 3, borderWidth: 1, borderColor: Colors.borderGlow, backgroundColor: 'rgba(0,255,255,0.06)' },
  etaText: { color: Colors.textMuted, fontFamily: Fonts.mono, fontSize: 9, letterSpacing: 1 },
});
