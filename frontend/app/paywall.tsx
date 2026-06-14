import React, { useEffect, useState } from 'react';
import {
  View, Text, StyleSheet, ScrollView, TouchableOpacity, Alert, ActivityIndicator,
} from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { useRouter } from 'expo-router';
import AsyncStorage from '@react-native-async-storage/async-storage';
import * as InAppPurchases from 'expo-in-app-purchases';
import { Colors, Fonts } from '../src/theme';
import { SystemFrame } from '../src/components/SystemFrame';
import { verifyPurchase } from '../src/api';

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
  const [connecting, setConnecting] = useState(true);
  const [product, setProduct] = useState<any>(null);

  useEffect(() => {
    let mounted = true;
    (async () => {
      try {
        await InAppPurchases.connectAsync();
        const { responseCode, results } = await InAppPurchases.getProductsAsync([PRODUCT_ID]);
        if (mounted && responseCode === InAppPurchases.IAPResponseCode.OK && results?.length) {
          setProduct(results[0]);
        }
      } catch (e) {
        // IAP not available in dev/simulator — continue anyway
      } finally {
        if (mounted) setConnecting(false);
      }

      InAppPurchases.setPurchaseListener(async ({ responseCode, results, errorCode }) => {
        if (responseCode === InAppPurchases.IAPResponseCode.OK && results?.length) {
          for (const purchase of results) {
            if (!purchase.acknowledged) {
              await InAppPurchases.finishTransactionAsync(purchase, true);
            }
          }
          await handlePurchaseSuccess();
        } else if (responseCode === InAppPurchases.IAPResponseCode.USER_CANCELED) {
          setLoading(false);
        } else {
          setLoading(false);
          Alert.alert('[SYSTEM ERROR]', `Purchase failed (code: ${errorCode})`);
        }
      });
    })();
    return () => { mounted = false; };
  }, []);

  const handlePurchaseSuccess = async () => {
    try {
      const profileId = await AsyncStorage.getItem('profile_id');
      if (profileId) {
        await verifyPurchase(profileId);
      }
      await AsyncStorage.setItem('has_paid', 'true');
      router.replace('/(tabs)/dashboard');
    } catch (e) {
      Alert.alert('[SYSTEM]', 'Purchase recorded. Welcome, Hunter.');
      router.replace('/(tabs)/dashboard');
    }
  };

  const handlePurchase = async () => {
    setLoading(true);
    try {
      await InAppPurchases.purchaseItemAsync(PRODUCT_ID);
    } catch (e: any) {
      setLoading(false);
      Alert.alert('[SYSTEM ERROR]', e?.message || 'Purchase failed');
    }
  };

  const handleRestore = async () => {
    setLoading(true);
    try {
      const { responseCode, results } = await InAppPurchases.getPurchaseHistoryAsync();
      if (responseCode === InAppPurchases.IAPResponseCode.OK && results?.length) {
        const found = results.find((p: any) => p.productId === PRODUCT_ID);
        if (found) {
          await handlePurchaseSuccess();
          return;
        }
      }
      Alert.alert('[SYSTEM]', 'No previous purchase found.');
    } catch (e: any) {
      Alert.alert('[SYSTEM ERROR]', e?.message || 'Restore failed');
    } finally {
      setLoading(false);
    }
  };

  return (
    <SafeAreaView style={styles.safe}>
      <ScrollView contentContainerStyle={styles.scroll}>
        <Text style={styles.locked}>[ACCESS LOCKED]</Text>
        <Text style={styles.rank}>HUNTER RANK: RESTRICTED</Text>
        <Text style={styles.lore}>
          // You have proven your worth in battle.{'\n'}
          // The System recognizes your potential.{'\n'}
          // Ascend beyond D-Rank. Unlock your true path.
        </Text>

        <SystemFrame style={styles.featuresFrame} color={Colors.primary}>
          <Text style={styles.featuresTitle}>// UNLOCK FULL ACCESS</Text>
          <Text style={styles.featuresSubtitle}>One-time purchase — no subscriptions</Text>
          {FEATURES.map((f, i) => (
            <View key={i} style={styles.featureRow}>
              <Text style={styles.featureIcon}>▶</Text>
              <Text style={styles.featureText}>{f}</Text>
            </View>
          ))}
        </SystemFrame>

        {connecting ? (
          <ActivityIndicator color={Colors.primary} style={{ marginVertical: 30 }} />
        ) : (
          <>
            <TouchableOpacity
              style={[styles.purchaseBtn, loading && styles.purchaseBtnDisabled]}
              onPress={handlePurchase}
              disabled={loading}
              testID="btn-purchase"
            >
              {loading ? (
                <ActivityIndicator color={Colors.bg} />
              ) : (
                <>
                  <Text style={styles.purchaseTxt}>UNLOCK FULL ACCESS</Text>
                  {product && (
                    <Text style={styles.priceHint}>{product.priceString}</Text>
                  )}
                </>
              )}
            </TouchableOpacity>

            <TouchableOpacity style={styles.restoreBtn} onPress={handleRestore} disabled={loading} testID="btn-restore">
              <Text style={styles.restoreTxt}>Restore Purchase</Text>
            </TouchableOpacity>
          </>
        )}

        <TouchableOpacity style={styles.laterBtn} onPress={() => router.replace('/(tabs)/dashboard')} testID="btn-later">
          <Text style={styles.laterTxt}>// Maybe Later</Text>
        </TouchableOpacity>
      </ScrollView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  safe: { flex: 1, backgroundColor: '#000000' },
  scroll: { padding: 24, paddingBottom: 60, alignItems: 'center' },
  locked: {
    color: '#FF0055',
    fontFamily: Fonts.heading,
    fontSize: 22,
    letterSpacing: 4,
    marginTop: 30,
    textShadowColor: 'rgba(255,0,85,0.6)',
    textShadowRadius: 16,
  },
  rank: {
    color: Colors.primary,
    fontFamily: Fonts.heading,
    fontSize: 16,
    letterSpacing: 3,
    marginTop: 10,
    textShadowColor: Colors.primaryGlow,
    textShadowRadius: 10,
  },
  lore: {
    color: Colors.textMuted,
    fontFamily: Fonts.mono,
    fontSize: 11,
    letterSpacing: 1,
    lineHeight: 20,
    textAlign: 'center',
    marginTop: 20,
    marginBottom: 30,
  },
  featuresFrame: { width: '100%', marginBottom: 30 },
  featuresTitle: {
    color: Colors.primary,
    fontFamily: Fonts.monoBold,
    fontSize: 13,
    letterSpacing: 2,
    marginBottom: 4,
  },
  featuresSubtitle: {
    color: Colors.textMuted,
    fontFamily: Fonts.mono,
    fontSize: 10,
    letterSpacing: 1,
    marginBottom: 16,
  },
  featureRow: { flexDirection: 'row', alignItems: 'center', paddingVertical: 6, gap: 10 },
  featureIcon: { color: Colors.primary, fontFamily: Fonts.monoBold, fontSize: 12 },
  featureText: { color: Colors.textMain, fontFamily: Fonts.mono, fontSize: 13, letterSpacing: 1 },
  purchaseBtn: {
    width: '100%',
    backgroundColor: Colors.primary,
    paddingVertical: 18,
    alignItems: 'center',
    shadowColor: Colors.primary,
    shadowOpacity: 0.6,
    shadowRadius: 16,
    marginBottom: 16,
  },
  purchaseBtnDisabled: { opacity: 0.6 },
  purchaseTxt: { color: '#000000', fontFamily: Fonts.heading, fontSize: 18, letterSpacing: 3 },
  priceHint: { color: 'rgba(0,0,0,0.7)', fontFamily: Fonts.mono, fontSize: 11, marginTop: 4 },
  restoreBtn: { paddingVertical: 12, marginBottom: 20 },
  restoreTxt: { color: Colors.textMuted, fontFamily: Fonts.mono, fontSize: 12, letterSpacing: 1, textDecorationLine: 'underline' },
  laterBtn: { paddingVertical: 12 },
  laterTxt: { color: Colors.textDim, fontFamily: Fonts.mono, fontSize: 11, letterSpacing: 2 },
});
