export const Colors = {
  bg: '#000000',
  surface: '#050505',
  surfaceElev: '#0A0A0A',
  primary: '#00FFFF',
  primaryDeep: '#0088AA',
  primaryGlow: 'rgba(0,255,255,0.5)',
  danger: '#FF0055',
  dangerGlow: 'rgba(255,0,85,0.5)',
  textMain: '#E0E0E0',
  textMuted: '#888888',
  textDim: '#555555',
  border: '#1A1A1A',
  borderGlow: 'rgba(0,255,255,0.2)',
  questNew: '#00FFFF',
  questComplete: '#00FF00',
  bossWarning: '#FF0000',
};

export const Fonts = {
  heading: 'Rajdhani_700Bold',
  headingBlack: 'Rajdhani_700Bold',
  body: 'JetBrainsMono_400Regular',
  mono: 'JetBrainsMono_500Medium',
  monoBold: 'JetBrainsMono_700Bold',
};

export const rankColor = (rank: string) => {
  switch (rank) {
    case 'E': return '#888888';
    case 'D': return '#7CFFCB';
    case 'C': return '#00FFFF';
    case 'B': return '#7C9DFF';
    case 'A': return '#C77CFF';
    case 'S': return '#FFD700';
    default: return '#888888';
  }
};

export const rankGlow = (rank: string) => {
  switch (rank) {
    case 'E': return 'rgba(136,136,136,0.4)';
    case 'D': return 'rgba(124,255,203,0.5)';
    case 'C': return 'rgba(0,255,255,0.6)';
    case 'B': return 'rgba(124,157,255,0.6)';
    case 'A': return 'rgba(199,124,255,0.7)';
    case 'S': return 'rgba(255,215,0,0.8)';
    default: return 'rgba(136,136,136,0.4)';
  }
};
