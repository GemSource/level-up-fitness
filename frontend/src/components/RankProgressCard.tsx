import React from 'react';
import { View, Text, StyleSheet } from 'react-native';
import { Colors, Fonts, rankColor } from '../theme';
import { SystemFrame } from './SystemFrame';
import { RankBadge } from './RankBadge';
import { XPBar } from './XPBar';

interface Props {
  data: any;            // /rank-progress response
  compact?: boolean;
}

export const RankProgressCard: React.FC<Props> = ({ data, compact }) => {
  if (!data) return null;
  const rc = rankColor(data.current_rank);
  const nextC = rankColor(data.next_rank);
  const pct = Math.max(2, Math.min(100, data.progress_pct));

  return (
    <SystemFrame style={[styles.frame, compact && styles.compact]} color={nextC}>
      <View style={styles.headerRow}>
        <View style={styles.badgeRow}>
          <RankBadge rank={data.current_rank} size={compact ? 36 : 52} />
          <Text style={styles.arrow}>→</Text>
          <RankBadge rank={data.next_rank} size={compact ? 36 : 52} />
        </View>
        <View style={{ alignItems: 'flex-end' }}>
          <Text style={styles.label}>NEXT RANK</Text>
          <Text style={[styles.nextRankTitle, { color: nextC }]}>
            {data.next_rank} ({data.next_threshold_kg}KG)
          </Text>
        </View>
      </View>

      <View style={styles.totalRow}>
        <Text style={[styles.totalNum, { color: rc }]}>{data.current_total}</Text>
        <Text style={styles.totalDiv}>/</Text>
        <Text style={styles.threshold}>{data.next_threshold_kg} KG</Text>
        <Text style={[styles.pctTag, { color: nextC }]}>{pct.toFixed(1)}%</Text>
      </View>

      <View style={styles.barBg}>
        <View style={[styles.barFill, { width: `${pct}%`, backgroundColor: nextC, shadowColor: nextC }]} />
      </View>

      {data.remaining_kg > 0 && (
        <Text style={styles.remaining}>{data.remaining_kg.toFixed(1)} KG REMAINING</Text>
      )}

      {!compact && data.lift_contributions && Object.keys(data.lift_contributions).length > 0 && (
        <View style={styles.contribWrap}>
          <Text style={styles.label}>// SUGGESTED LIFT GAINS</Text>
          <View style={styles.contribRow}>
            <View style={styles.contribCol}>
              <Text style={styles.contribLift}>SQUAT</Text>
              <Text style={[styles.contribVal, { color: nextC }]}>+{data.lift_contributions.squat}</Text>
              <Text style={styles.contribUnit}>KG</Text>
            </View>
            <View style={styles.contribCol}>
              <Text style={styles.contribLift}>BENCH</Text>
              <Text style={[styles.contribVal, { color: nextC }]}>+{data.lift_contributions.bench}</Text>
              <Text style={styles.contribUnit}>KG</Text>
            </View>
            <View style={styles.contribCol}>
              <Text style={styles.contribLift}>DEAD</Text>
              <Text style={[styles.contribVal, { color: nextC }]}>+{data.lift_contributions.deadlift}</Text>
              <Text style={styles.contribUnit}>KG</Text>
            </View>
          </View>
        </View>
      )}

      {!compact && data.xp && (
        <View style={styles.xpWrap}>
          <XPBar current={data.xp.current} max={data.xp.next_level_xp} level={data.xp.level} />
        </View>
      )}

      {!compact && data.projected_weeks && data.projected_weeks.max > 0 && (
        <Text style={styles.projection}>
          ⌖ EST. {data.next_rank} RANK: {data.projected_weeks.min}–{data.projected_weeks.max} WEEKS
        </Text>
      )}

      <Text style={[styles.message, { color: data.rank_up ? Colors.questComplete : Colors.textMain }]}>
        {data.message}
      </Text>
    </SystemFrame>
  );
};

const styles = StyleSheet.create({
  frame: { marginBottom: 12 },
  compact: { padding: 12 },
  headerRow: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', marginBottom: 14 },
  badgeRow: { flexDirection: 'row', alignItems: 'center', gap: 8 },
  arrow: { color: Colors.primary, fontFamily: Fonts.heading, fontSize: 18 },
  label: { color: Colors.primary, fontFamily: Fonts.monoBold, fontSize: 9, letterSpacing: 2 },
  nextRankTitle: { fontFamily: Fonts.heading, fontSize: 14, letterSpacing: 2, marginTop: 2 },
  totalRow: { flexDirection: 'row', alignItems: 'baseline', gap: 6, marginBottom: 8 },
  totalNum: { fontFamily: Fonts.heading, fontSize: 28, letterSpacing: 1 },
  totalDiv: { color: Colors.textDim, fontFamily: Fonts.heading, fontSize: 18 },
  threshold: { color: Colors.textMuted, fontFamily: Fonts.mono, fontSize: 13, letterSpacing: 1 },
  pctTag: { marginLeft: 'auto', fontFamily: Fonts.monoBold, fontSize: 14, letterSpacing: 1 },
  barBg: { height: 10, backgroundColor: '#080808', borderWidth: 1, borderColor: Colors.borderGlow, overflow: 'hidden' },
  barFill: { height: '100%', shadowOpacity: 1, shadowRadius: 8, shadowOffset: { width: 0, height: 0 } },
  remaining: { color: Colors.textMuted, fontFamily: Fonts.monoBold, fontSize: 11, letterSpacing: 2, marginTop: 6 },
  contribWrap: { marginTop: 14, paddingTop: 12, borderTopWidth: 1, borderTopColor: Colors.border },
  contribRow: { flexDirection: 'row', justifyContent: 'space-between', marginTop: 8 },
  contribCol: { flex: 1, alignItems: 'center' },
  contribLift: { color: Colors.textMuted, fontFamily: Fonts.mono, fontSize: 9, letterSpacing: 2 },
  contribVal: { fontFamily: Fonts.monoBold, fontSize: 20, marginTop: 4 },
  contribUnit: { color: Colors.textDim, fontFamily: Fonts.mono, fontSize: 9, letterSpacing: 1 },
  xpWrap: { marginTop: 14, paddingTop: 12, borderTopWidth: 1, borderTopColor: Colors.border },
  projection: { color: Colors.primary, fontFamily: Fonts.monoBold, fontSize: 10, letterSpacing: 2, marginTop: 10, textAlign: 'center' },
  message: { fontFamily: Fonts.mono, fontSize: 11, lineHeight: 16, marginTop: 12, paddingTop: 10, borderTopWidth: 1, borderTopColor: Colors.border, fontStyle: 'italic' },
});
