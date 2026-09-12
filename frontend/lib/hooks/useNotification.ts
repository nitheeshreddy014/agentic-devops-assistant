/**
 * Browser Notification API hook.
 * Requests permission once; fires a notification when investigation completes.
 */
import { useEffect, useRef } from 'react';

export function useNotification() {
  const permissionRef = useRef<NotificationPermission>('default');

  useEffect(() => {
    if (typeof Notification !== 'undefined') {
      permissionRef.current = Notification.permission;
      if (Notification.permission === 'default') {
        Notification.requestPermission().then(p => { permissionRef.current = p; });
      }
    }
  }, []);

  const notify = (title: string, body: string) => {
    if (typeof Notification === 'undefined') return;
    if (permissionRef.current === 'granted' && document.hidden) {
      new Notification(title, { body, icon: '/favicon.ico' });
    }
  };

  return { notify };
}
