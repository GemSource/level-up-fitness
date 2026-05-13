import React, { useCallback, useState } from 'react';
import { View, Text, StyleSheet, ScrollView, TouchableOpacity, Alert } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { useFocusEffect, useRouter } from 'expo-router';
import AsyncStorage from '@react-native-async-storage/async-storage';
import { Ionicons } from '@expo/vector-icons';
import { Colors, Fonts } from '../../src/theme';
import { SystemFrame } from '../../src/components/SystemFrame';
import { listSideQuests, logSideQuest } from '../../src/api';

export default function SideQuests() {
  const router = useRouter();
  const [quests, setQuests] = useState<any[]>([]);

  const load = async () => {
    const id = await AsyncStorage.getItem('profile_id');
    if (!id) return;
    const r = await listSideQuests(id);
    setQuests(r);
  };

  useFocusEffect(useCallback(() => { load(); }, []));

  return (
    <SafeAreaView style={styles.safe}>
      <View style={styles.header}>
        <TouchableOpacity onPress={() => router.back()} testID="btn-back">
          <Ionicons name="chevron-back" size={24} color={Colors.primary} />
        </TouchableOpacity>
        <View style={{ flex: 1, marginLeft: 8 }}>
          <Text style={styles.system}>[SIDE QUESTS]</Text>
          <Text style={styles.title}>OPTIONAL MISSIONS</Text>
        </View>
        <TouchableOpacity onPress={() => router.push('/side-quests/create')} testID="btn-new-sq" style={styles.newBtn}>
          <Ionicons name="add" size={18} color={Colors.primary} />
          <Text style={styles.newTxt}>NEW</Text>
        </TouchableOpacity>
      </View>

      <ScrollView contentContainerStyle={styles.scroll}>
        {quests.length === 0 ? (
          <SystemFrame style={styles.empty}>
            <Text style={styles.emptyTxt}>No side quests yet.{'\n'}Side quests are optional bonus missions — they earn reduced XP and don't unlock boss fights.</Text>
            <TouchableOpacity onPress={() => router.push('/side-quests/create')} style={styles.createBtn} testID="btn-create-first">
              <Text style={styles.createTxt}>CREATE FIRST QUEST</Text>
            </TouchableOpacity>
          </SystemFrame>
        ) : (
          quests.slice().reverse().map(q => (
            <TouchableOpacity
              key={q.id}
              onPress={() => router.push(`/side-quests/${q.id}`)}
              disabled={q.completed}
              testID={`sq-${q.id}`}
            >
              <SystemFrame style={[styles.card, q.completed && styles.cardDone]} color={q.completed ? Colors.questComplete : Colors.primary}>
                <View style={styles.cardHead}>
                  <Text style={styles.cardName}>{q.name}</Text>
                  {q.completed ? (
                    <Ionicons name="checkmark-circle" size={20} color={Colors.questComplete} />
                  ) : (
                    <Ionicons name="chevron-forward" size={20} color={Colors.primary} />
                  )}
                </View>
                <Text style={styles.cardMeta}>
                  {q.exercises.length} EXERCISES{q.xp_gained ? ` · +${q.xp_gained} XP` : ''}
                </Text>
              </SystemFrame>
            </TouchableOpacity>
          ))
        )}
      </ScrollView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  safe: { flex: 1, backgroundColor: Colors.bg },
  header: { flexDirection: 'row', alignItems: 'center', padding: 16 },
  system: { color: Colors.primary, fontFamily: Fonts.mono, fontSize: 10, letterSpacing: 2 },
  title: { color: Colors.textMain, fontFamily: Fonts.heading, fontSize: 20, letterSpacing: 2, marginTop: 2 },
  newBtn: { flexDirection: 'row', alignItems: 'center', gap: 4, paddingHorizontal: 10, paddingVertical: 6, borderWidth: 1, borderColor: Colors.primary, backgroundColor: 'rgba(0,255,255,0.06)' },
  newTxt: { color: Colors.primary, fontFamily: Fonts.monoBold, fontSize: 11, letterSpacing: 1 },
  scroll: { padding: 16, paddingBottom: 40 },
  empty: { alignItems: 'center', padding: 20 },
  emptyTxt: { color: Colors.textMuted, fontFamily: Fonts.mono, fontSize: 12, textAlign: 'center', lineHeight: 18 },
  createBtn: { marginTop: 14, paddingHorizontal: 16, paddingVertical: 10, borderWidth: 1, borderColor: Colors.primary, backgroundColor: 'rgba(0,255,255,0.08)' },
  createTxt: { color: Colors.primary, fontFamily: Fonts.monoBold, fontSize: 12, letterSpacing: 2 },
  card: { marginBottom: 10 },
  cardDone: { opacity: 0.6 },
  cardHead: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center' },
  cardName: { color: Colors.textMain, fontFamily: Fonts.heading, fontSize: 16, letterSpacing: 1 },
  cardMeta: { color: Colors.textMuted, fontFamily: Fonts.mono, fontSize: 10, letterSpacing: 1, marginTop: 4 },
});
