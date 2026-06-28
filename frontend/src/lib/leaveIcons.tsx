import {
  Baby,
  Briefcase,
  Calendar,
  Gift,
  Handshake,
  Heart,
  Home,
  Moon,
  Plane,
  Stethoscope,
  Sun,
  Umbrella,
  type LucideIcon,
} from 'lucide-react';

// Іконки типів відсутностей. Ключ зберігається у LeaveType.icon, рендер — на фронті.
export const LEAVE_ICON_OPTIONS: Array<{ key: string; label: string; Icon: LucideIcon }> = [
  { key: 'plane', label: 'Літак', Icon: Plane },
  { key: 'briefcase', label: 'Портфель', Icon: Briefcase },
  { key: 'handshake', label: 'Рукостискання', Icon: Handshake },
  { key: 'home', label: 'Дім', Icon: Home },
  { key: 'heart', label: 'Серце', Icon: Heart },
  { key: 'baby', label: 'Малюк', Icon: Baby },
  { key: 'moon', label: 'Місяць', Icon: Moon },
  { key: 'sun', label: 'Сонце', Icon: Sun },
  { key: 'umbrella', label: 'Парасоля', Icon: Umbrella },
  { key: 'stethoscope', label: 'Стетоскоп', Icon: Stethoscope },
  { key: 'gift', label: 'Подарунок', Icon: Gift },
  { key: 'calendar', label: 'Календар', Icon: Calendar },
];

const ICON_BY_KEY: Record<string, LucideIcon> = Object.fromEntries(
  LEAVE_ICON_OPTIONS.map((item) => [item.key, item.Icon]),
);

export function LeaveTypeIcon({ iconKey, size = 16 }: { iconKey: string; size?: number }) {
  const Icon = ICON_BY_KEY[iconKey] ?? Calendar;
  return <Icon size={size} />;
}
