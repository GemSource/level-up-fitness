import React from 'react';
import { View, Text, StyleSheet } from 'react-native';
import { Colors, Fonts } from '../theme';

interface Props {
  current: number;
  max: number;
  level: number;
  label?: string;
}

export const XPBar: React.FC<Props> = ({ current, max, level, label = 'EXP' }) => {
  const pct = Math.min(100, Math.round((current / max) * 100));
  return (
    <View testID="xp-bar" style={styles.wrap}>
      <View style={styles.headerRow}>
        <Text style={styles.label}>{label}  ::  LV {level}</Text>
        <Text style={styles.value}>{current} / {max}</Text>
      </View>
      <View style={styles.barBg}>
        <View style={[styles.barFill, { width: `${pct}%` }]} />
        <View style={styles.scan} />
      </View>
    </View>
  );
};

const styles = StyleSheet.create({
  wrap: { width: '100%' },
  headerRow: { flexDirection: 'row', justifyContent: 'space-between', marginBottom: 6 },
  label: { color: Colors.primary, fontFamily: Fonts.monoBold, fontSize: 11, letterSpacing: 2 },
  value: { color: Colors.textMain, fontFamily: Fonts.mono, fontSize: 11, letterSpacing: 1 },
  barBg: {
    height: 10,
    backgroundColor: '#080808',
    borderWidth: 1,
    borderColor: Colors.borderGlow,
    overflow: 'hidden',
  },
  barFill: {
    height: '100%',
    backgroundColor: Colors.primary,
    shadowColor: Colors.primary,
    shadowOpacity: 1,
    shadowRadius: 8,
    shadowOffset: { width: 0, height: 0 },
  },
  scan: {
    position: 'absolute',
    top: 0,
    bottom: 0,
    width: 2,
    right: 0,
    backgroundColor: '#fff',
    opacity: 0.6,
  },
});
