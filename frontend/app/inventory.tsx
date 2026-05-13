import React, { useCallback, useState } from 'react';
import { View, Text, StyleSheet, ScrollView, TouchableOpacity, Alert } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { useFocusEffect, useRouter } from 'expo-router';
import AsyncStorage from '@react-native-async-storage/async-storage';
import { Ionicons } from '@expo/vector-icons';
import { Colors, Fonts } from '../src/theme';
import { SystemFrame } from '../src/components/SystemFrame';
import { getInventory, activateItem } from '../src/api';

export default function Inventory() {
  const router = useRouter();
  const [data, setData] = useState<any>(null);

  const load = async () => {
    const id = await AsyncStorage.getItem('profile_id');
    if (!id) { router.replace('/onboarding'); return; }
    const d = await getInventory(id);
    setData(d);
  };

  useFocusEffect(useCallback(() => { load(); }, []));

  const activate = async (key: string, name: string) => {
    const id = await AsyncStorage.getItem('profile_id');
    if (!id) return;
    try {
      await activateItem(id, key);
      Alert.alert('[ACTIVATED]', `${name} is now active. Effect applies on your next eligible session.`);
      load();
    } catch (e: any) {
      Alert.alert('[SYSTEM]', e?.response?.data?.detail || e?.message || 'Failed');
    }
  };

  if (!data) {
    return <SafeAreaView style={styles.safe}><Text style={styles.system}>[LOADING...]</Text></SafeAreaView>;
  }

  return (
    <SafeAreaView style={styles.safe}>
      <View style={styles.header}>
        <TouchableOpacity onPress={() => router.back()} testID="btn-back">
          <Ionicons name="chevron-back" size={24} color={Colors.primary} />
        </TouchableOpacity>
        <View style={{ flex: 1, marginLeft: 8 }}>
          <Text style={styles.system}>[INVENTORY]</Text>
          <Text style={styles.title}>HUNTER CACHE</Text>
        </View>
        <View style={styles.coinBox}>
          <Ionicons name="diamond" size={16} color="#FFD700" />
          <Text style={styles.coinTxt}>{data.coins}</Text>
        </View>
      </View>

      <ScrollView contentContainerStyle={styles.scroll}>
        {data.active_buffs && data.active_buffs.length > 0 && (
          <>
            <Text style={styles.sectionLabel}>// ACTIVE BUFFS · {data.active_buffs.length} / 2</Text>
            {data.active_buffs.map((b: any, i: number) => (
              <SystemFrame key={i} style={styles.buffCard} color={Colors.questComplete}>
                <Text style={styles.buffName}>★ {b.item_key.replace(/_/g, ' ').toUpperCase()}</Text>
                <Text style={styles.buffDesc}>Scope: {b.scope}{b.expires_at ? ` · expires ${new Date(b.expires_at).toLocaleDateString()}` : ''}</Text>
              </SystemFrame>
            ))}
          </>
        )}
        <Text style={styles.sectionLabel}>// ITEMS · {data.items.length}</Text>
        {data.items.length === 0 ? (
          <SystemFrame style={styles.empty}>
            <Text style={styles.emptyTxt}>No items yet. Complete quests to earn loot drops, or visit the shop.</Text>
            <TouchableOpacity onPress={() => router.push('/shop')} style={styles.shopLink} testID="btn-goto-shop">
              <Text style={styles.shopLinkTxt}>OPEN SHOP ›</Text>
            </TouchableOpacity>
          </SystemFrame>
        ) : (
          data.items.map((item: any) => (
            <SystemFrame key={item.key} style={styles.itemCard} color={item.rarity_color}>
              <View style={styles.rowTop}>
                <View style={{ flex: 1 }}>
                  <View style={styles.nameRow}>
                    <Text style={styles.itemName}>{item.name}</Text>
                    <View style={[styles.rarityTag, { borderColor: item.rarity_color }]}>
                      <Text style={[styles.rarityTxt, { color: item.rarity_color }]}>{item.rarity.toUpperCase()}</Text>
                    </View>
                  </View>
                  <Text style={styles.itemDesc}>{item.desc}</Text>
                </View>
                <View style={styles.qtyBox}>
                  <Text style={styles.qty}>×{item.quantity}</Text>
                </View>
              </View>
              <TouchableOpacity
                testID={`activate-${item.key}`}
                onPress={() => activate(item.key, item.name)}
                style={styles.actBtn}
              >
                <Ionicons name="flash" size={14} color={Colors.primary} />
                <Text style={styles.actTxt}>ACTIVATE</Text>
              </TouchableOpacity>
            </SystemFrame>
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
  coinBox: { flexDirection: 'row', alignItems: 'center', gap: 6, paddingHorizontal: 10, paddingVertical: 6, borderWidth: 1, borderColor: '#FFD700', backgroundColor: 'rgba(255,215,0,0.06)' },
  coinTxt: { color: '#FFD700', fontFamily: Fonts.monoBold, fontSize: 14 },
  scroll: { padding: 16, paddingBottom: 40 },
  sectionLabel: { color: Colors.primary, fontFamily: Fonts.monoBold, fontSize: 11, letterSpacing: 3, marginBottom: 10, marginTop: 6 },
  buffCard: { marginBottom: 8 },
  buffName: { color: Colors.questComplete, fontFamily: Fonts.heading, fontSize: 14, letterSpacing: 1 },
  buffDesc: { color: Colors.textMuted, fontFamily: Fonts.mono, fontSize: 10, marginTop: 4 },
  empty: { alignItems: 'center', paddingVertical: 24 },
  emptyTxt: { color: Colors.textMuted, fontFamily: Fonts.mono, fontSize: 12, textAlign: 'center' },
  shopLink: { marginTop: 12, paddingHorizontal: 16, paddingVertical: 10, borderWidth: 1, borderColor: Colors.primary, backgroundColor: 'rgba(0,255,255,0.08)' },
  shopLinkTxt: { color: Colors.primary, fontFamily: Fonts.monoBold, fontSize: 12, letterSpacing: 2 },
  itemCard: { marginBottom: 10 },
  rowTop: { flexDirection: 'row', alignItems: 'flex-start' },
  nameRow: { flexDirection: 'row', alignItems: 'center', gap: 8 },
  itemName: { color: Colors.textMain, fontFamily: Fonts.heading, fontSize: 15, letterSpacing: 1 },
  rarityTag: { paddingHorizontal: 5, paddingVertical: 1, borderWidth: 1, backgroundColor: '#000' },
  rarityTxt: { fontFamily: Fonts.monoBold, fontSize: 8, letterSpacing: 1 },
  itemDesc: { color: Colors.textMuted, fontFamily: Fonts.mono, fontSize: 11, marginTop: 4 },
  qtyBox: { paddingHorizontal: 8, paddingVertical: 4, borderWidth: 1, borderColor: Colors.borderGlow },
  qty: { color: Colors.primary, fontFamily: Fonts.monoBold, fontSize: 12 },
  actBtn: { flexDirection: 'row', alignItems: 'center', justifyContent: 'center', gap: 6, marginTop: 10, paddingVertical: 10, borderWidth: 1, borderColor: Colors.primary, backgroundColor: 'rgba(0,255,255,0.06)' },
  actTxt: { color: Colors.primary, fontFamily: Fonts.monoBold, fontSize: 12, letterSpacing: 2 },
});
