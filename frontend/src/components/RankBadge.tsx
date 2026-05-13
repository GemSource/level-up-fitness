import React from 'react';
import { View, Text, StyleSheet } from 'react-native';
import { Fonts, rankColor, rankGlow } from '../theme';

interface Props {
  rank: string;
  size?: number;
}

export const RankBadge: React.FC<Props> = ({ rank, size = 80 }) => {
  const color = rankColor(rank);
  const glow = rankGlow(rank);
  return (
    <View
      testID={`rank-badge-${rank}`}
      style={[
        styles.badge,
        {
          width: size,
          height: size,
          borderColor: color,
          shadowColor: color,
          backgroundColor: '#000',
        },
      ]}
    >
      <View style={[styles.inner, { borderColor: color + '80' }]}>
        <Text style={[styles.rankText, { color, fontSize: size * 0.5, textShadowColor: glow, textShadowRadius: 12 }]}>
          {rank}
        </Text>
      </View>
    </View>
  );
};

const styles = StyleSheet.create({
  badge: {
    borderWidth: 2,
    alignItems: 'center',
    justifyContent: 'center',
    shadowOpacity: 0.9,
    shadowRadius: 16,
    shadowOffset: { width: 0, height: 0 },
    elevation: 12,
  },
  inner: {
    width: '85%',
    height: '85%',
    borderWidth: 1,
    alignItems: 'center',
    justifyContent: 'center',
  },
  rankText: {
    fontFamily: Fonts.heading,
    fontWeight: '900',
    letterSpacing: 2,
    textShadowOffset: { width: 0, height: 0 },
  },
});
