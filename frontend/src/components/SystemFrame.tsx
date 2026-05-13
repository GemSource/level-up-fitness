import React from 'react';
import { View, StyleSheet, ViewStyle } from 'react-native';
import { Colors } from '../theme';

interface Props {
  children: React.ReactNode;
  style?: ViewStyle | ViewStyle[];
  glow?: boolean;
  color?: string;
  testID?: string;
}

export const SystemFrame: React.FC<Props> = ({ children, style, glow = true, color = Colors.primary, testID }) => {
  return (
    <View testID={testID} style={[styles.frame, { borderColor: color + '40' }, glow && { shadowColor: color, shadowOpacity: 0.25, shadowRadius: 12, shadowOffset: { width: 0, height: 0 } }, style]}>
      {/* corner accents */}
      <View style={[styles.corner, styles.cornerTL, { borderColor: color }]} />
      <View style={[styles.corner, styles.cornerTR, { borderColor: color }]} />
      <View style={[styles.corner, styles.cornerBL, { borderColor: color }]} />
      <View style={[styles.corner, styles.cornerBR, { borderColor: color }]} />
      {children}
    </View>
  );
};

const styles = StyleSheet.create({
  frame: {
    backgroundColor: Colors.surface,
    borderWidth: 1,
    padding: 16,
    position: 'relative',
  },
  corner: {
    position: 'absolute',
    width: 10,
    height: 10,
  },
  cornerTL: { top: -1, left: -1, borderTopWidth: 2, borderLeftWidth: 2 },
  cornerTR: { top: -1, right: -1, borderTopWidth: 2, borderRightWidth: 2 },
  cornerBL: { bottom: -1, left: -1, borderBottomWidth: 2, borderLeftWidth: 2 },
  cornerBR: { bottom: -1, right: -1, borderBottomWidth: 2, borderRightWidth: 2 },
});
