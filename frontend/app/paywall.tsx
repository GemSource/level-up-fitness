import React, { useEffect, useState } from 'react';
import {
  View, Text, StyleSheet, ScrollView, TouchableOpacity, Alert, ActivityIndicator,
} from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { useRouter } from 'expo-router';
import AsyncStorage from '@react-native-async-storage/async-storage';
import { Ionicons } from '@expo/vector-icons';
import * as IAP from 'expo-in-app-purchases';
import { Colors, Fonts } from '../src/theme';
import { SystemFrame } from '../src/components/SystemFrame';
import { verifyPurchase } from '../src/api';

const PRODUCT_ID = 'level_up_fitness_premium';

const FEATURES = [
  'Progress beyond D-Rank to C, B, A & S',
  'All future Boss Fights unlocked',
  'Unlimited workout & cardio logging',
  'AI Coach access',
  'Hunter Shop & Inventory',
  'Side Quests & custom workouts',
];

export default function Paywall() {
  const router = useRouter();
  const [product, setProduct] = useState<IAP.IAPItemDetails | null>(null);
  const [loading, setLoading] = useState(true);
  const [purchasing, setPurchasing] = useState(false);

  useEffect(() => {
    let connected = false;
    (async () => {
      try {
        await IAP.connectAsync();
        connected = true;
        const { responseCode, results } = await IAP.getProductsAsync([PRODUCT_ID]);
        if (responseCode === IAP.IAPResponseCode.OK && results?.length) {
          setProduct(results[0]);
        }
      } catch {
        // IAP unavailable (simulator / no connection) — still show the screen
      } finally {
        setLoading(false);
      }

      IAP.setPurchaseListener(async ({ responseCode, results, errorCode }) => {
        if (responseCode === IAP.IAPResponseCode.OK && results?.length) {
          const purchase = results[0];
          if (!purchase.acknowledged) {
            await IAP.finishTransactionAsync(purchase, false);
          }
          await handlePurchaseSuccess();
        } else if (responseCode === IAP.IAPResponseCode.USER_CANCELED) {
          setPurchasing(false);
        } else {
          setPurchasing(false);
          Alert.alert('[SYSTEM ERROR]', `Purchase failed (${errorCode}). Try again.`);
        }
      });
    })();

    return () => {
      if (connected) IAP.disconnectAsync();
    };
  }, []);

  const handlePurchaseSuccess = async () => {
    try {
      const pid = await AsyncStorage.getItem('profile_id');
      if (pid) await verifyPurchase(pid);
      await AsyncStorage.setItem('has_paid', 'true');
    } catch {}
    setPurchasing(false);
    router.replace('/(tabs)/dashboard');
  };

  const purchase = async () => {
    if (!product) {
      Alert.alert('[SYSTEM]', 'Store unavailable. Please check your connection and try again.');
      return;
    }
    setPurchasing(true);
    try {
      await IAP.purchaseItemAsync(PRODUCT_ID);
    } catch {
      setPurchasing(false);
      Alert.alert('[SYSTEM ERROR]', 'Could not initiate purchase.');
    }
  };

  const restore = async () => {
    setPurchasing(true);
    try {
      await IAP.connectAsync();
      const { responseCode, results } = await IAP.getPurchaseHistoryAsync();
      if (responseCode === IAP.IAPResponseCode.OK && results?.some(r => r.productId === PRODUCT_ID)) {
        await handlePurchaseSuccess();
      } else {
        setPurchasing(false);
        Alert.alert('[SYSTEM]', 'No previous purchase found for this account.');
      }
    } catch {
      setPurchasing(false);
      Alert.alert('[SYSTEM ERROR]', 'Could not restore purchases.');
    }
  };

  const priceLabel = product?.price ?? '—';

  return (
    <SafeAreaView style={styles.safe}>
      <ScrollView contentContainerStyle={styles.scroll}>
        <View style={styles.header}>
          <TouchableOpacity onPress={() => router.replace('/(tabs)/dashboard')} testID="btn-later">
            <Text style={styles.laterTxt}>MAYBE LATER</Text>
          </TouchableOpacity>
        </View>

        <View style={styles.iconWrap}>
          <Ionicons name="lock-open-outline" size={56} color={Colors.primary} style={styles.icon} />
        </View>

        <Text style={styles.eyebrow}>// ACCESS PROTOCOL</Text>
        <Text style={styles.title}>ASCEND FURTHER</Text>
        <Text style={styles.sub}>
          You have defeated your first boss and proven yourself worthy.{'\n'}
          Unlock the full Hunter Strength System to continue your rise.
        </Text>

        <SystemFrame style={styles.featuresFrame} color={Colors.primary}>
          <Text style={styles.featuresTitle}>// FULL HUNTER ACCESS</Text>
          {FEATURES.map((f, i) => (
            <View key={i} style={styles.featureRow}>
              <Ionicons name="checkmark-circle" size={16} color={Colors.questComplete} />
              <Text style={styles.featureTxt}>{f}</Text>
            </View>
          ))}
        </SystemFrame>

        {loading ? (
          <ActivityIndicator color={Colors.primary} style={{ marginVertical: 32 }} />
        ) : (
          <TouchableOpacity
            testID="btn-purchase"
            style={[styles.purchaseBtn, purchasing && styles.purchaseBtnDisabled]}
            onPress={purchase}
            disabled={purchasing}
          >
            {purchasing ? (
              <ActivityIndicator color={Colors.bg} />
            ) : (
              <>
                <Text style={styles.purchaseTxt}>UNLOCK — {priceLabel}</Text>
                <Text style={styles.purchaseSub}>ONE-TIME PURCHASE · NO SUBSCRIPTION</Text>
              </>
            )}
          </TouchableOpacity>
        )}

        <TouchableOpacity onPress={restore} disabled={purchasing} style={styles.restoreBtn} testID="btn-restore">
          <Text style={styles.restoreTxt}>Restore Purchase</Text>
        </TouchableOpacity>

        <Text style={styles.legal}>
          Payment will be charged to your Apple ID account. Purchase is non-refundable.
        </Text>
      </ScrollView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  safe: { flex: 1, backgroundColor: Colors.bg },
  scroll: { padding: 24, paddingBottom: 48 },
  header: { alignItems: 'flex-end', marginBottom: 8 },
  laterTxt: { color: Colors.textMuted, fontFamily: Fonts.mono, fontSize: 11, letterSpacing: 2 },
  iconWrap: { alignItems: 'center', marginTop: 16, marginBottom: 8 },
  icon: { textShadowColor: Colors.primaryGlow, textShadowRadius: 20 },
  eyebrow: { color: Colors.primary, fontFamily: Fonts.mono, fontSize: 10, letterSpacing: 3, textAlign: 'center', marginBottom: 8 },
  title: { color: Colors.textMain, fontFamily: Fonts.heading, fontSize: 32, letterSpacing: 4, textAlign: 'center', textShadowColor: Colors.primaryGlow, textShadowRadius: 16 },
  sub: { color: Colors.textMuted, fontFamily: Fonts.mono, fontSize: 11, letterSpacing: 1, textAlign: 'center', marginTop: 12, marginBottom: 28, lineHeight: 18 },
  featuresFrame: { marginBottom: 28 },
  featuresTitle: { color: Colors.primary, fontFamily: Fonts.monoBold, fontSize: 10, letterSpacing: 2, marginBottom: 14 },
  featureRow: { flexDirection: 'row', alignItems: 'center', gap: 10, paddingVertical: 6, borderBottomWidth: 1, borderBottomColor: Colors.border },
  featureTxt: { color: Colors.textMain, fontFamily: Fonts.mono, fontSize: 13, flex: 1 },
  purchaseBtn: {
    backgroundColor: Colors.primary,
    paddingVertical: 18,
    alignItems: 'center',
    shadowColor: Colors.primary,
    shadowOpacity: 0.7,
    shadowRadius: 18,
    marginBottom: 16,
  },
  purchaseBtnDisabled: { opacity: 0.6 },
  purchaseTxt: { color: Colors.bg, fontFamily: Fonts.heading, fontSize: 18, letterSpacing: 3 },
  purchaseSub: { color: Colors.bg, fontFamily: Fonts.mono, fontSize: 9, letterSpacing: 2, marginTop: 4, opacity: 0.7 },
  restoreBtn: { alignItems: 'center', paddingVertical: 12, marginBottom: 24 },
  restoreTxt: { color: Colors.textMuted, fontFamily: Fonts.mono, fontSize: 11, letterSpacing: 1, textDecorationLine: 'underline' },
  legal: { color: Colors.textDim, fontFamily: Fonts.mono, fontSize: 9, textAlign: 'center', lineHeight: 14 },
});
