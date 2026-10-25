import type { SlotIconName } from './types';

export const DEFAULT_SLOT_ICONS: (SlotIconName | null)[] = ['math', 'golf', 'car', 'shovel'];
export const SLOT_ICON_LABELS: Record<SlotIconName, string> = {
  math: 'Matematiikka', golf: 'Golf', car: 'Auto', shovel: 'Lapio',
};

const SOURCES: Record<SlotIconName, string> = {
  math: new URL('./assets/slot-math.svg', import.meta.url).href,
  golf: new URL('./assets/slot-golf.svg', import.meta.url).href,
  car: new URL('./assets/slot-car.svg', import.meta.url).href,
  shovel: new URL('./assets/slot-shovel.svg', import.meta.url).href,
};

export function SlotIcon({ icon }: { icon: SlotIconName | null }) {
  return icon ? <img className="slot-icon-image" src={SOURCES[icon]} alt={SLOT_ICON_LABELS[icon]} draggable={false} /> : null;
}
