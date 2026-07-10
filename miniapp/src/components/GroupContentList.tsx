import type { GroupMember } from '../types';
import { formatPrice } from '../api';
import { itemTypeLabel } from '../utils/itemType';
import { InlineContentPanel } from './InlineContentPanel';
import { IconLock } from './Icons';
import { SafeImage } from './SafeImage';

function memberHasInlineContent(member: GroupMember) {
  if (member.is_downloadable && member.download_url) return true;
  return (member.media || []).some((m) => m.type !== 'image' && !m.locked && m.url);
}

export function GroupContentList({
  members,
  parentType,
}: {
  members: GroupMember[];
  parentType: 'course' | 'package';
}) {
  if (!members.length) return null;

  const title = parentType === 'course' ? 'قسمت‌های دوره' : 'فایل‌های پکیج';

  return (
    <div className="mt-6">
      <h2 className="mb-3 text-xs font-bold uppercase tracking-wide text-muted">{title}</h2>
      <div className="space-y-3">
        {members.map((member, index) => {
          const canUse = !member.locked && member.has_access;
          const hasContent = memberHasInlineContent(member);

          return (
            <div
              key={member.id}
              className={`overflow-hidden rounded-2xl border ${
                member.locked
                  ? 'border-border bg-[var(--color-bg)] opacity-90'
                  : 'border-border bg-surface'
              }`}
            >
              <div className="flex items-center gap-3 p-3">
                <span className="flex h-8 w-8 shrink-0 items-center justify-center rounded-xl bg-[var(--color-primary-soft)] text-xs font-bold text-primary">
                  {index + 1}
                </span>
                {member.image ? (
                  <SafeImage
                    src={member.image}
                    className="h-12 w-12 shrink-0 rounded-xl object-cover"
                    fallback={<span className="h-12 w-12 shrink-0 rounded-xl bg-neutral-100" />}
                  />
                ) : null}
                <div className="min-w-0 flex-1">
                  <div className="flex flex-wrap items-center gap-2">
                    <span className="text-sm font-semibold leading-snug">{member.title}</span>
                    <span className="item-type-chip !py-0.5 text-[10px]">
                      {itemTypeLabel(member.item_type)}
                    </span>
                  </div>
                  {member.short_description && (
                    <p className="mt-0.5 text-xs text-muted">{member.short_description}</p>
                  )}
                </div>
                <div className="shrink-0">
                  {member.locked ? (
                    <span className="inline-flex items-center gap-1 text-xs text-muted">
                      <IconLock className="h-3.5 w-3.5" />
                      قفل
                    </span>
                  ) : member.is_preview ? (
                    <span className="text-xs font-medium text-primary">پیش‌نمایش</span>
                  ) : member.has_access ? (
                    <span className="text-xs font-medium text-emerald-600">آماده</span>
                  ) : member.is_buyable ? (
                    <span className="text-xs text-muted">{formatPrice(member.price)}</span>
                  ) : null}
                </div>
              </div>

              {canUse && (
                <div className="border-t border-border px-3 pb-3 pt-2">
                  {hasContent ? (
                    <InlineContentPanel source={member} />
                  ) : (
                    <p className="rounded-xl bg-[var(--color-bg)] px-3 py-2 text-xs text-muted">
                      محتوایی برای نمایش در این بخش ثبت نشده است.
                    </p>
                  )}
                </div>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}
