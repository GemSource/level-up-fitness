import React, { useCallback, useState } from 'react';
import { View, Text, StyleSheet, ScrollView, TouchableOpacity, Alert } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { useFocusEffect, useRouter } from 'expo-router';
import AsyncStorage from '@react-native-async-storage/async-storage';
import { Ionicons } from '@expo/vector-icons';
import { Colors, Fonts } from '../src/theme';
import { SystemFrame } from '../src/components/SystemFrame';
import { getShopCatalog, getInventory, buyItem } from '../src/api';

const CATS = [
  { key: 'all', label: 'ALL' },
  { key: 'training', label: 'TRAINING' },
  { key: 'recovery', label: 'RECOVERY' },
  { key: 'xp', label: 'XP' },
  { key: 'boss', label: 'BOSS' },
];

export default function Shop() {
  const router = useRouter();
  const [catalog, setCatalog] = useState<any[]>([]);
  const [coins, setCoins] = useState(0);
  const [activeCat, setActiveCat] = useState('all');
  const [buying, setBuying] = useState<string | null>(null);

  const load = async () => {
    const id = await AsyncStorage.getItem('profile_id');
    if (!id) { router.replace('/onboarding'); return; }
    const [c, inv] = await Promise.all([getShopCatalog(), getInventory(id)]);
    setCatalog(c);
    setCoins(inv.coins);
  };

  useFocusEffect(useCallback(() => { load(); }, []));

  const purchase = async (item: any) => {
    const id = await AsyncStorage.getItem('profile_id');
    if (!id) return;
    setBuying(item.key);
    try {
      const r = await buyItem(id, item.key);
      setCoins(r.coins);
      Alert.alert('[ACQUIRED]', `${item.name}\n-${item.price} Hunter Coins\nBalance: ${r.coins}`);
    } catch (e: any) {
      const d = e?.response?.data?.detail;
      if (d && d.error === 'insufficient_coins') {
        Alert.alert('[SYSTEM]', `Not enough coins. Need ${d.need}, have ${d.have}.`);
      } else {
        Alert.alert('[SYSTEM ERROR]', e?.message || 'Failed');
      }
    } finally {
      setBuying(null);
    }
  };

  const filtered = activeCat === 'all' ? catalog : catalog.filter(c => c.category === activeCat);

  return (
    <SafeAreaView style={styles.safe}>
      <View style={styles.header}>
        <TouchableOpacity onPress={() => router.back()} testID="btn-back">
          <Ionicons name="chevron-back" size={24} color={Colors.primary} />
        </TouchableOpacity>
        <View style={{ flex: 1, marginLeft: 8 }}>
          <Text style={styles.system}>[HUNTER SHOP]</Text>
          <Text style={styles.title}>BLACK MARKET</Text>
        </View>
        <View style={styles.coinBox}>
          <Ionicons name="diamond" size={16} color="#FFD700" />
          <Text style={styles.coinTxt}>{coins}</Text>
        </View>
      </View>

      <ScrollView horizontal showsHorizontalScrollIndicator={false} contentContainerStyle={styles.catRow}>
        {CATS.map(c => (
          <TouchableOpacity
            key={c.key}
            testID={`shop-cat-${c.key}`}
            onPress={() => setActiveCat(c.key)}
            style={[styles.catPill, activeCat === c.key && styles.catActive]}
          >
            <Text style={[styles.catTxt, activeCat === c.key && styles.catTxtActive]}>{c.label}</Text>
          </TouchableOpacity>
        ))}
      </ScrollView>

      <ScrollView contentContainerStyle={styles.scroll}>
        {filtered.map(item => (
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
            </View>
            <TouchableOpacity
              testID={`buy-${item.key}`}
              onPress={() => purchase(item)}
              style={[styles.buyBtn, coins < item.price && styles.buyBtnLocked]}
              disabled={coins < item.price || buying === item.key}
            >
              <Ionicons name="diamond" size={14} color={coins < item.price ? Colors.textDim : Colors.primary} />
              <Text style={[styles.buyTxt, coins < item.price && { color: Colors.textDim }]}>
                {buying === item.key ? 'BUYING...' : `${item.price} COINS`}
              </Text>
            </TouchableOpacity>
          </SystemFrame>
        ))}
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
  catRow: { paddingHorizontal: 16, gap: 6, paddingBottom: 8 },
  catPill: { paddingHorizontal: 12, paddingVertical: 6, borderWidth: 1, borderColor: Colors.border, backgroundColor: '#000' },
  catActive: { borderColor: Colors.primary, backgroundColor: 'rgba(0,255,255,0.08)' },
  catTxt: { color: Colors.textMuted, fontFamily: Fonts.monoBold, fontSize: 10, letterSpacing: 2 },
  catTxtActive: { color: Colors.primary },
  scroll: { padding: 16, paddingBottom: 40 },
  itemCard: { marginBottom: 10 },
  rowTop: { flexDirection: 'row', alignItems: 'flex-start' },
  nameRow: { flexDirection: 'row', alignItems: 'center', gap: 8 },
  itemName: { color: Colors.textMain, fontFamily: Fonts.heading, fontSize: 15, letterSpacing: 1 },
  rarityTag: { paddingHorizontal: 5, paddingVertical: 1, borderWidth: 1, backgroundColor: '#000' },
  rarityTxt: { fontFamily: Fonts.monoBold, fontSize: 8, letterSpacing: 1 },
  itemDesc: { color: Colors.textMuted, fontFamily: Fonts.mono, fontSize: 11, marginTop: 4 },
  buyBtn: { flexDirection: 'row', alignItems: 'center', justifyContent: 'center', gap: 6, marginTop: 10, paddingVertical: 10, borderWidth: 1, borderColor: Colors.primary, backgroundColor: 'rgba(0,255,255,0.06)' },
  buyBtnLocked: { borderColor: Colors.border, backgroundColor: '#0a0a0a' },
  buyTxt: { color: Colors.primary, fontFamily: Fonts.monoBold, fontSize: 12, letterSpacing: 2 },
});
