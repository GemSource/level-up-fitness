import React, { useEffect, useState } from 'react';
import {
  View, Text, StyleSheet, ScrollView, TouchableOpacity, Alert, ActivityIndicator,
} from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { useRouter } from 'expo-router';
import AsyncStorage from '@react-native-async-storage/async-storage';
import { Colors, Fonts } from '../src/theme';
import { SystemFrame } from '../src/components/SystemFrame';
import { verifyPurchase } from '../src/api';
import * as InAppPurchases from 'expo-in-app-purchases';

const PRODUCT_ID = 'level_up_fitness_premium';

const FEATURES = [
  'Continue past D-Rank',
  'All Boss Fights',
  'Unlimited Workout Logging',
  'AI Coach',
  'Shop & Inventory',
];

export default function Paywall() {
  const router = useRouter();
  const [loading, setLoading] = useState(false);
  const [products, setProducts] = useState<InAppPurchases.IAPItemDetails[]>([]);

  useEffect(() => {
    (async () => {
      try {
        await InAppPurchases.connectAsync();
        const { results } = await InAppPurchases.getProductsAsync([PRODUCT_ID]);
        if (results) setProducts(results);

        InAppPurchases.setPurchaseListener(async ({ responseCode, results: purchaseResults, errorCode }) => {
          if (responseCode === InAppPurchases.IAPResponseCode.OK && purchaseResults) {
            for (const purchase of purchaseResults) {
              if (!purchase.acknowledged) {
                await InAppPurchases.finishTransactionAsync(purchase, false);
                const profileId = await AsyncStorage.getItem('profile_id');
                if (profileId) {
                  try {
                    await verifyPurchase(profileId);
                  } catch {}
                }
                await AsyncStorage.setItem('has_paid', 'true');
                setLoading(false);
                router.replace('/(tabs)/dashboard');
              }
            }
          } else if (responseCode === InAppPurchases.IAPResponseCode.USER_CANCELED) {
            setLoading(false);
          } else {
            setLoading(false);
            Alert.alert('[SYSTEM ERROR]', `Purchase failed. Code: ${errorCode}`);
          }
        });
      } catch (e) {
        // IAP not available in dev/simulator
      }
    })();

    return () => {
      InAppPurchases.disconnectAsync().catch(() => {});
    };
  }, []);

  const handlePurchase = async () => {
    setLoading(true);
    try {
      await InAppPurchases.purchaseItemAsync(PRODUCT_ID);
    } catch (e: any) {
      setLoading(false);
      Alert.alert('[SYSTEM ERROR]', e?.message || 'Purchase unavailable.');
    }
  };

  const handleRestore = async () => {
    setLoading(true);
    try {
      await InAppPurchases.connectAsync();
      const history = await InAppPurchases.getPurchaseHistoryAsync();
      const hasPurchase = history?.results?.some(p => p.productId === PRODUCT_ID);
      if (hasPurchase) {
        const profileId = await AsyncStorage.getItem('profile_id');
        if (profileId) {
          try {
            await verifyPurchase(profileId);
          } catch {}
        }
        await AsyncStorage.setItem('has_paid', 'true');
        router.replace('/(tabs)/dashboard');
      } else {
        Alert.alert('[SYSTEM]', 'No previous purchase found.');
      }
    } catch (e: any) {
      Alert.alert('[SYSTEM ERROR]', e?.message || 'Restore failed.');
    } finally {
      setLoading(false);
    }
  };

  const product = products[0];
  const priceStr = product?.price ?? '—';

  return (
    <SafeAreaView style={styles.safe}>
      <ScrollView contentContainerStyle={styles.scroll}>
        <Text style={styles.lockTag}>[ACCESS LOCKED]</Text>
        <Text style={styles.rank}>HUNTER RANK: RESTRICTED</Text>
        <Text style={styles.lore}>
          {'// You have proven yourself worthy.\n// The system acknowledges your potential.\n// But the path beyond E-Rank demands commitment.'}
        </Text>

        <SystemFrame style={styles.card} color={Colors.primary}>
          <Text style={styles.cardTitle}>UNLOCK FULL ACCESS</Text>
          <Text style={styles.cardSub}>One-time purchase — no subscription</Text>
          <View style={styles.divider} />
          {FEATURES.map((f, i) => (
            <View key={i} style={styles.featureRow}>
              <Text style={styles.featureDot}>▸</Text>
              <Text style={styles.featureText}>{f}</Text>
            </View>
          ))}
        </SystemFrame>

        <TouchableOpacity
          style={[styles.purchaseBtn, loading && { opacity: 0.6 }]}
          onPress={handlePurchase}
          disabled={loading}
        >
          {loading ? (
            <ActivityIndicator color={Colors.bg} />
          ) : (
            <Text style={styles.purchaseTxt}>
              UNLOCK — {priceStr}
            </Text>
          )}
        </TouchableOpacity>

        <TouchableOpacity style={styles.restoreBtn} onPress={handleRestore} disabled={loading}>
          <Text style={styles.restoreTxt}>Restore Purchase</Text>
        </TouchableOpacity>

        <TouchableOpacity style={styles.laterBtn} onPress={() => router.replace('/(tabs)/dashboard')}>
          <Text style={styles.laterTxt}>// Maybe Later</Text>
        </TouchableOpacity>
      </ScrollView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  safe: { flex: 1, backgroundColor: '#000000' },
  scroll: { padding: 24, paddingBottom: 60, alignItems: 'center' },
  lockTag: {
    color: '#FF0055',
    fontFamily: Fonts.monoBold,
    fontSize: 11,
    letterSpacing: 4,
    marginTop: 30,
    textShadowColor: '#FF0055',
    textShadowRadius: 12,
  },
  rank: {
    color: '#00FFFF',
    fontFamily: Fonts.heading,
    fontSize: 22,
    letterSpacing: 3,
    marginTop: 12,
    textShadowColor: '#00FFFF',
    textShadowRadius: 14,
  },
  lore: {
    color: Colors.textMuted,
    fontFamily: Fonts.mono,
    fontSize: 11,
    letterSpacing: 1,
    marginTop: 20,
    marginBottom: 28,
    textAlign: 'center',
    lineHeight: 20,
  },
  card: { width: '100%', marginBottom: 28 },
  cardTitle: {
    color: '#00FFFF',
    fontFamily: Fonts.heading,
    fontSize: 18,
    letterSpacing: 3,
    marginBottom: 4,
    textShadowColor: '#00FFFF',
    textShadowRadius: 10,
  },
  cardSub: {
    color: Colors.textMuted,
    fontFamily: Fonts.mono,
    fontSize: 10,
    letterSpacing: 1,
    marginBottom: 14,
  },
  divider: { height: 1, backgroundColor: 'rgba(0,255,255,0.2)', marginBottom: 14 },
  featureRow: { flexDirection: 'row', alignItems: 'center', paddingVertical: 6 },
  featureDot: { color: '#00FFFF', fontFamily: Fonts.monoBold, fontSize: 14, marginRight: 10 },
  featureText: { color: Colors.textMain, fontFamily: Fonts.mono, fontSize: 13, letterSpacing: 1 },
  purchaseBtn: {
    width: '100%',
    backgroundColor: '#00FFFF',
    paddingVertical: 18,
    alignItems: 'center',
    shadowColor: '#00FFFF',
    shadowOpacity: 0.7,
    shadowRadius: 16,
    marginBottom: 16,
  },
  purchaseTxt: {
    color: '#000000',
    fontFamily: Fonts.heading,
    fontSize: 18,
    letterSpacing: 4,
  },
  restoreBtn: {
    paddingVertical: 12,
    paddingHorizontal: 20,
  },
  restoreTxt: {
    color: Colors.textMuted,
    fontFamily: Fonts.mono,
    fontSize: 12,
    letterSpacing: 1,
    textDecorationLine: 'underline',
  },
  laterBtn: { marginTop: 16 },
  laterTxt: {
    color: '#FF0055',
    fontFamily: Fonts.mono,
    fontSize: 11,
    letterSpacing: 2,
  },
});
