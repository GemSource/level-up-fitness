import React, { useCallback, useState, useMemo } from 'react';
import { View, Text, StyleSheet, ScrollView, TouchableOpacity } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { useFocusEffect, useRouter } from 'expo-router';
import AsyncStorage from '@react-native-async-storage/async-storage';
import { Ionicons } from '@expo/vector-icons';
import { Colors, Fonts, rankColor } from '../../src/theme';
import { SystemFrame } from '../../src/components/SystemFrame';
import { RankBadge } from '../../src/components/RankBadge';
import { getAchievements, getProfile } from '../../src/api';

const RANKS = ['E', 'D', 'C', 'B', 'A', 'S'];

const TIER_COLOR: Record<string, string> = {
  basic: '#7CFFCB',
  medium: '#00FFFF',
  major: '#C77CFF',
  elite: '#FFD700',
};

const CATEGORY_ORDER = [
  'Rank', 'Quests', 'Weekly', 'Streak',
  'Squat', 'Bench', 'Deadlift', 'Total',
  'Elite', 'Volume', 'Quality',
  'Run', 'Pace', 'Sprint', 'Bike',
  'Hybrid', 'Boss', 'Special',
];

export default function Rank() {
  const router = useRouter();
  const [achievements, setAchievements] = useState<any[]>([]);
  const [profile, setProfile] = useState<any>(null);
  const [activeCat, setActiveCat] = useState<string>('ALL');

  const load = async () => {
    const id = await AsyncStorage.getItem('profile_id');
    if (!id) { router.replace('/onboarding'); return; }
    const [a, p] = await Promise.all([getAchievements(id), getProfile(id)]);
    setAchievements(a);
    setProfile(p);
  };

  useFocusEffect(useCallback(() => { load(); }, []));

  const grouped = useMemo(() => {
    const map: Record<string, any[]> = {};
    achievements.forEach(a => {
      const c = a.category || 'Special';
      if (!map[c]) map[c] = [];
      map[c].push(a);
    });
    return map;
  }, [achievements]);

  const cats = useMemo(() => {
    const present = Object.keys(grouped);
    return CATEGORY_ORDER.filter(c => present.includes(c));
  }, [grouped]);

  const filtered = activeCat === 'ALL' ? achievements : (grouped[activeCat] || []);
  const unlockedCount = achievements.filter(a => a.unlocked).length;

  if (!profile) {
    return <SafeAreaView style={styles.safe}><Text style={styles.system}>[LOADING...]</Text></SafeAreaView>;
  }

  return (
    <SafeAreaView style={styles.safe}>
      <ScrollView contentContainerStyle={styles.scroll}>
        <Text style={styles.system}>[HUNTER ARCHIVE]</Text>
        <Text style={styles.title}>RANK & TROPHIES</Text>
        <Text style={styles.unlockedStat}>
          UNLOCKED: {unlockedCount} / {achievements.length}
        </Text>

        <Text style={styles.sectionLabel}>// RANK PROGRESSION</Text>
        <View style={styles.rankLadder}>
          {RANKS.map((r) => {
            const active = r === profile.rank;
            const past = RANKS.indexOf(r) < RANKS.indexOf(profile.rank);
            return (
              <View key={r} style={[styles.rankStep, { opacity: past || active ? 1 : 0.35 }]}>
                <RankBadge rank={r} size={active ? 64 : 44} />
                {active && <Text style={[styles.youBadge, { color: rankColor(r) }]}>// YOU</Text>}
              </View>
            );
          })}
        </View>

        <Text style={styles.sectionLabel}>// ACHIEVEMENTS</Text>
        <ScrollView
          horizontal
          showsHorizontalScrollIndicator={false}
          contentContainerStyle={styles.catRow}
        >
          <TouchableOpacity
            testID="cat-ALL"
            onPress={() => setActiveCat('ALL')}
            style={[styles.catPill, activeCat === 'ALL' && styles.catPillActive]}
          >
            <Text style={[styles.catTxt, activeCat === 'ALL' && styles.catTxtActive]}>ALL · {achievements.length}</Text>
          </TouchableOpacity>
          {cats.map(c => {
            const u = (grouped[c] || []).filter(a => a.unlocked).length;
            const tot = (grouped[c] || []).length;
            return (
              <TouchableOpacity
                key={c}
                testID={`cat-${c}`}
                onPress={() => setActiveCat(c)}
                style={[styles.catPill, activeCat === c && styles.catPillActive]}
              >
                <Text style={[styles.catTxt, activeCat === c && styles.catTxtActive]}>{c.toUpperCase()} {u}/{tot}</Text>
              </TouchableOpacity>
            );
          })}
        </ScrollView>

        {filtered.map((a) => {
          const tier = a.tier || 'basic';
          const tierColor = TIER_COLOR[tier];
          return (
            <SystemFrame
              key={a.key}
              style={[styles.achCard, !a.unlocked && styles.achLocked]}
              color={a.unlocked ? tierColor : Colors.border}
              glow={a.unlocked}
            >
              <View style={styles.achRow}>
                <Ionicons
                  name={a.unlocked ? 'trophy' : 'lock-closed'}
                  size={22}
                  color={a.unlocked ? tierColor : Colors.textDim}
                />
                <View style={{ flex: 1, marginLeft: 12 }}>
                  <View style={styles.achHeadRow}>
                    <Text style={[styles.achName, !a.unlocked && { color: Colors.textDim }]}>{a.name}</Text>
                    <View style={[styles.tierTag, { borderColor: tierColor }]}>
                      <Text style={[styles.tierTxt, { color: tierColor }]}>{tier.toUpperCase()} +{a.xp}</Text>
                    </View>
                  </View>
                  <Text style={styles.achDesc}>{a.desc}</Text>
                </View>
              </View>
            </SystemFrame>
          );
        })}
      </ScrollView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  safe: { flex: 1, backgroundColor: Colors.bg },
  scroll: { padding: 16, paddingBottom: 40 },
  system: { color: Colors.primary, fontFamily: Fonts.mono, fontSize: 10, letterSpacing: 3 },
  title: { color: Colors.textMain, fontFamily: Fonts.heading, fontSize: 22, letterSpacing: 1, marginTop: 2 },
  unlockedStat: { color: Colors.textMuted, fontFamily: Fonts.mono, fontSize: 11, letterSpacing: 2, marginTop: 6, marginBottom: 16 },
  sectionLabel: { color: Colors.primary, fontFamily: Fonts.monoBold, fontSize: 11, letterSpacing: 3, marginBottom: 12, marginTop: 8 },
  rankLadder: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', marginBottom: 20, paddingVertical: 12 },
  rankStep: { alignItems: 'center' },
  youBadge: { fontFamily: Fonts.monoBold, fontSize: 8, letterSpacing: 2, marginTop: 4 },
  catRow: { flexDirection: 'row', gap: 6, paddingBottom: 12, paddingRight: 12 },
  catPill: { paddingHorizontal: 10, paddingVertical: 6, borderWidth: 1, borderColor: Colors.border, backgroundColor: '#000' },
  catPillActive: { borderColor: Colors.primary, backgroundColor: 'rgba(0,255,255,0.08)' },
  catTxt: { color: Colors.textMuted, fontFamily: Fonts.monoBold, fontSize: 10, letterSpacing: 1 },
  catTxtActive: { color: Colors.primary },
  achCard: { marginBottom: 8, paddingVertical: 12 },
  achLocked: { opacity: 0.5 },
  achRow: { flexDirection: 'row', alignItems: 'center' },
  achHeadRow: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', gap: 6 },
  achName: { color: Colors.textMain, fontFamily: Fonts.heading, fontSize: 14, letterSpacing: 1, flex: 1 },
  achDesc: { color: Colors.textMuted, fontFamily: Fonts.mono, fontSize: 11, marginTop: 2 },
  tierTag: { paddingHorizontal: 6, paddingVertical: 2, borderWidth: 1, backgroundColor: '#000' },
  tierTxt: { fontFamily: Fonts.monoBold, fontSize: 8, letterSpacing: 1 },
});
