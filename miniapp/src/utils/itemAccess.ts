import type { CatalogItem } from '../types';

/** کاربر به محتوای قابل‌خرید این آیتم (دوره/پکیج/محصول) دسترسی دارد. */
export function userOwnsCatalogItem(item: CatalogItem): boolean {
  if (item.has_access) return true;
  if (!item.is_group_parent || !item.group_members?.length) return false;

  const nonPreview = item.group_members.filter((member) => !member.is_preview);
  if (!nonPreview.length) return false;

  const lockedPaid = nonPreview.filter((member) => member.locked);
  if (!lockedPaid.length) {
    return nonPreview.every((member) => member.has_access);
  }
  return lockedPaid.every((member) => member.has_access);
}

export function canAddItemToCart(item: CatalogItem, canPurchase = true): boolean {
  if (!canPurchase) return false;
  if (!item.is_buyable) return false;
  return !userOwnsCatalogItem(item);
}
