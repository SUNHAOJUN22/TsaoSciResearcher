import React from 'react';
import { cn } from '@/lib/utils';

interface UserAvatarProps {
  name?: string;
  avatar?: string;
  className?: string;
  alt?: string;
}

const SAFE_AVATAR_PREFIXES = [
  'data:image/png;base64,',
  'data:image/jpeg;base64,',
  'data:image/webp;base64,',
];

export function isSafeAvatarDataUrl(value?: string): value is string {
  return Boolean(value && SAFE_AVATAR_PREFIXES.some((prefix) => value.startsWith(prefix)));
}

function getInitials(name?: string): string {
  const normalized = name?.trim();
  if (!normalized) return 'DB';

  const parts = normalized.split(/\s+/).filter(Boolean);
  if (parts.length === 1) {
    return Array.from(parts[0]).slice(0, 2).join('').toUpperCase();
  }
  return `${Array.from(parts[0])[0] ?? ''}${Array.from(parts.at(-1) ?? '')[0] ?? ''}`.toUpperCase();
}

export const UserAvatar: React.FC<UserAvatarProps> = ({ name, avatar, className, alt }) => {
  const safeAvatar = isSafeAvatarDataUrl(avatar) ? avatar : undefined;

  return (
    <span
      className={cn(
        'inline-flex items-center justify-center overflow-hidden bg-slate-200 font-bold text-slate-700 dark:bg-slate-800 dark:text-slate-200',
        className,
      )}
      aria-label={alt || name || 'User avatar'}
    >
      {safeAvatar ? (
        <img src={safeAvatar} alt={alt || name || 'User avatar'} className="h-full w-full object-cover" />
      ) : (
        <span aria-hidden="true">{getInitials(name)}</span>
      )}
    </span>
  );
};
