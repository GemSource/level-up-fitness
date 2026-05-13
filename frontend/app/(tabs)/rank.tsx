import React, { useCallback, useState } from 'react';
import { View, Text, StyleSheet, ScrollView } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { useFocusEffect, useRouter } from 'expo-router';
import AsyncStorage from '@react-native-async-storage/async-storage';
import { Ionicons } from '@expo/vector-icons';
import { Colors, Fonts, rankColor } from '../../src/theme';
import { SystemFrame } from '../../src/components/SystemFrame';
import { RankBadge } from '../../src/components/RankBadge';
import { getAchievements, getProfile } from '../../src/api';

const RANKS = ['E', 'D', 'C', 'B', 'A', 'S'];

export default function Rank() {
  const router = useRouter();
  const [achievements, setAchievements] = useState<any[]>([]);
  const [profile, setProfile] = useState<any>(null);

  const load = async () => {
    const id = await AsyncStorage.getItem('profile_id');
    if (!id) { router.replace('/onboarding'); return; }
    const [a, p] = await Promise.all([getAchievements(id), getProfile(id)]);
    setAchievements(a);
    setProfile(p);
  };

  useFocusEffect(useCallback(() => { load(); }, []));

  if (!profile) return <SafeAreaView style={styles.safe}><Text style={styles.system}>[LOADING...]</Text></SafeAreaView>;

  return (
    <SafeAreaView style={styles.safe}>
      <ScrollView contentContainerStyle={styles.scroll}>
        <Text style={styles.system}>[HUNTER ARCHIVE]</Text>
        <Text style={styles.title}>RANK & TROPHIES</Text>

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
        {achievements.map((a) => (
          <SystemFrame
            key={a.key}
            style={[styles.achCard, !a.unlocked && styles.achLocked]}
            color={a.unlocked ? Colors.primary : Colors.border}
            glow={a.unlocked}
          >
            <View style={styles.achRow}>
              <Ionicons
                name={a.unlocked ? 'trophy' : 'lock-closed'}
                size={22}
                color={a.unlocked ? Colors.primary : Colors.textDim}
              />
              <View style={{ flex: 1, marginLeft: 12 }}>
                <Text style={[styles.achName, !a.unlocked && { color: Colors.textDim }]}>{a.name}</Text>
                <Text style={styles.achDesc}>{a.desc}</Text>
              </View>
              {a.unlocked && <Text style={styles.unlockedTag}>UNLOCKED</Text>}
            </View>
          </SystemFrame>
        ))}
      </ScrollView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  safe: { flex: 1, backgroundColor: Colors.bg },
  scroll: { padding: 16, paddingBottom: 40 },
  system: { color: Colors.primary, fontFamily: Fonts.mono, fontSize: 10, letterSpacing: 3 },
  title: { color: Colors.textMain, fontFamily: Fonts.heading, fontSize: 22, letterSpacing: 1, marginTop: 2, marginBottom: 20 },
  sectionLabel: { color: Colors.primary, fontFamily: Fonts.monoBold, fontSize: 11, letterSpacing: 3, marginBottom: 12, marginTop: 8 },
  rankLadder: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', marginBottom: 20, paddingVertical: 12 },
  rankStep: { alignItems: 'center' },
  youBadge: { fontFamily: Fonts.monoBold, fontSize: 8, letterSpacing: 2, marginTop: 4 },
  achCard: { marginBottom: 8, paddingVertical: 12 },
  achLocked: { opacity: 0.5 },
  achRow: { flexDirection: 'row', alignItems: 'center' },
  achName: { color: Colors.textMain, fontFamily: Fonts.heading, fontSize: 15, letterSpacing: 1 },
  achDesc: { color: Colors.textMuted, fontFamily: Fonts.mono, fontSize: 11, marginTop: 2 },
  unlockedTag: { color: Colors.questComplete, fontFamily: Fonts.monoBold, fontSize: 9, letterSpacing: 2 },
});
