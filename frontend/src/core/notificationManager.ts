/**
 * Notification Manager - Ported from aureon_unified_ecosystem.py lines 2841-3000
 * Handles Telegram bot, Discord webhooks, and in-app notifications
 */

import { unifiedBus } from './unifiedBus';

type AlertLevel = 'TRADE' | 'PROFIT' | 'LOSS' | 'CIRCUIT' | 'ARBITRAGE' | 'SYSTEM' | 'INFO';

interface NotificationConfig {
  telegramEnabled: boolean;
  telegramBotToken?: string;
  telegramChatId?: string;
  discordEnabled: boolean;
  discordWebhookUrl?: string;
  inAppEnabled: boolean;
  minAlertLevel: AlertLevel;
  quietHoursStart?: number;
  quietHoursEnd?: number;
}

interface Notification {
  id: string;
  level: AlertLevel;
  title: string;
  message: string;
  timestamp: number;
  sent: boolean;
  channels: ('telegram' | 'discord' | 'inApp')[];
  metadata?: Record<string, any>;
}

const ALERT_PRIORITY: Record<AlertLevel, number> = {
  INFO: 0,
  TRADE: 1,
  PROFIT: 2,
  LOSS: 2,
  ARBITRAGE: 3,
  CIRCUIT: 4,
  SYSTEM: 5
};

const ALERT_EMOJI: Record<AlertLevel, string> = {
  INFO: 'ℹ️',
  TRADE: '📊',
  PROFIT: '💰',
  LOSS: '📉',
  ARBITRAGE: '🔄',
  CIRCUIT: '🚨',
  SYSTEM: '⚙️'
};

export class NotificationManager {
  private config: NotificationConfig = {
    telegramEnabled: false,
    discordEnabled: false,
    inAppEnabled: true,
    minAlertLevel: 'TRADE'
  };

  private notifications: Notification[] = [];
  private maxNotifications: number = 100;
  private subscribers: ((notification: Notification) => void)[] = [];

  constructor(config?: Partial<NotificationConfig>) {
    if (config) {
      this.config = { ...this.config, ...config };
    }
  }

  /**
   * Configure notification channels
   */
  configure(config: Partial<NotificationConfig>): void {
    this.config = { ...this.config, ...config };
    console.log('[NotificationManager] Configuration updated:', {
      telegramEnabled: this.config.telegramEnabled,
      discordEnabled: this.config.discordEnabled,
      inAppEnabled: this.config.inAppEnabled
    });
  }

  /**
   * Send notification across configured channels
   */
  async notify(level: AlertLevel, title: string, message: string, metadata?: Record<string, any>): Promise<void> {
    // Check if alert level meets minimum threshold
    if (ALERT_PRIORITY[level] < ALERT_PRIORITY[this.config.minAlertLevel]) {
      return;
    }

    // Check quiet hours
    if (this.isQuietHours()) {
      // Only allow CIRCUIT and SYSTEM alerts during quiet hours
      if (level !== 'CIRCUIT' && level !== 'SYSTEM') {
        return;
      }
    }

    const notification: Notification = {
      id: `notif-${crypto.randomUUID()}`,
      level,
      title,
      message,
      timestamp: Date.now(),
      sent: false,
      channels: [],
      metadata
    };

    const channels: Promise<boolean>[] = [];

    // Telegram
    if (this.config.telegramEnabled && this.config.telegramBotToken && this.config.telegramChatId) {
      channels.push(this.sendTelegram(notification));
    }

    // Discord
    if (this.config.discordEnabled && this.config.discordWebhookUrl) {
      channels.push(this.sendDiscord(notification));
    }

    // In-app
    if (this.config.inAppEnabled) {
      this.sendInApp(notification);
    }

    // Wait for external channels
    await Promise.allSettled(channels);

    // Store notification
    this.notifications.push(notification);
    if (this.notifications.length > this.maxNotifications) {
      this.notifications = this.notifications.slice(-this.maxNotifications);
    }

    // Notify subscribers
    for (const subscriber of this.subscribers) {
      try {
        subscriber(notification);
      } catch (error) {
        console.error('[NotificationManager] Subscriber error:', error);
      }
    }

    // Publish to UnifiedBus
    unifiedBus.publish({
      systemName: 'NotificationManager',
      timestamp: Date.now(),
      ready: true,
      coherence: 1,
      confidence: 1,
      signal: 'NEUTRAL',
      data: {
        lastNotification: notification.id,
        level,
        title
      }
    });
  }

  private async sendTelegram(notification: Notification): Promise<boolean> {
    try {
      const emoji = ALERT_EMOJI[notification.level];
      const text = `${emoji} *${notification.title}*\n\n${notification.message}`;

      // In browser environment, we'd call an edge function
      const response = await fetch('/api/notifications/telegram', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          botToken: this.config.telegramBotToken,
          chatId: this.config.telegramChatId,
          message: text,
          parseMode: 'Markdown'
        })
      });

      if (response.ok) {
        notification.channels.push('telegram');
        notification.sent = true;
        return true;
      }
      return false;
    } catch (error) {
      console.error('[NotificationManager] Telegram send failed:', error);
      return false;
    }
  }

  private async sendDiscord(notification: Notification): Promise<boolean> {
    try {
      const emoji = ALERT_EMOJI[notification.level];
      const color = this.getDiscordColor(notification.level);

      const payload = {
        embeds: [{
          title: `${emoji} ${notification.title}`,
          description: notification.message,
          color,
          timestamp: new Date(notification.timestamp).toISOString(),
          footer: {
            text: 'AUREON Trading System'
          }
        }]
      };

      const response = await fetch(this.config.discordWebhookUrl!, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      });

      if (response.ok) {
        notification.channels.push('discord');
        notification.sent = true;
        return true;
      }
      return false;
    } catch (error) {
      console.error('[NotificationManager] Discord send failed:', error);
      return false;
    }
  }

  private sendInApp(notification: Notification): void {
    notification.channels.push('inApp');
    notification.sent = true;
    console.log(`[NotificationManager] ${ALERT_EMOJI[notification.level]} ${notification.title}: ${notification.message}`);
  }

  private getDiscordColor(level: AlertLevel): number {
    const colors: Record<AlertLevel, number> = {
      INFO: 0x3498db,     // Blue
      TRADE: 0x9b59b6,    // Purple
      PROFIT: 0x2ecc71,   // Green
      LOSS: 0xe74c3c,     // Red
      ARBITRAGE: 0xf1c40f, // Yellow
      CIRCUIT: 0xe74c3c,  // Red
      SYSTEM: 0x95a5a6    // Gray
    };
    return colors[level];
  }

  private isQuietHours(): boolean {
    if (this.config.quietHoursStart === undefined || this.config.quietHoursEnd === undefined) {
      return false;
    }

    const hour = new Date().getUTCHours();
    const start = this.config.quietHoursStart;
    const end = this.config.quietHoursEnd;

    if (start < end) {
      return hour >= start && hour < end;
    } else {
      // Quiet hours span midnight
      return hour >= start || hour < end;
    }
  }

  /**
   * Subscribe to notifications
   */
  subscribe(callback: (notification: Notification) => void): () => void {
    this.subscribers.push(callback);
    return () => {
      this.subscribers = this.subscribers.filter(s => s !== callback);
    };
  }

  /**
   * Get recent notifications
   */
  getRecent(limit: number = 20): Notification[] {
    return this.notifications.slice(-limit).reverse();
  }

  /**
   * Get notifications by level
   */
  getByLevel(level: AlertLevel): Notification[] {
    return this.notifications.filter(n => n.level === level);
  }

  /**
   * Clear all notifications
   */
  clear(): void {
    this.notifications = [];
  }

  // Convenience methods for common alerts
  async notifyTrade(symbol: string, side: 'BUY' | 'SELL', price: number, quantity: number): Promise<void> {
    await this.notify('TRADE', `${side} ${symbol}`, 
      `Executed ${side} order for ${quantity} @ $${price.toFixed(2)}`);
  }

  async notifyProfit(symbol: string, profit: number, percentage: number): Promise<void> {
    await this.notify('PROFIT', `Profit on ${symbol}`,
      `Realized profit: $${profit.toFixed(2)} (${percentage.toFixed(2)}%)`);
  }

  async notifyLoss(symbol: string, loss: number, percentage: number): Promise<void> {
    await this.notify('LOSS', `Loss on ${symbol}`,
      `Realized loss: $${Math.abs(loss).toFixed(2)} (${percentage.toFixed(2)}%)`);
  }

  async notifyCircuitBreaker(reason: string): Promise<void> {
    await this.notify('CIRCUIT', 'Circuit Breaker Triggered',
      `Trading halted: ${reason}`, { critical: true });
  }

  async notifyArbitrage(opportunity: { symbol: string; spread: number; exchanges: string[] }): Promise<void> {
    await this.notify('ARBITRAGE', 'Arbitrage Opportunity',
      `${opportunity.symbol}: ${opportunity.spread.toFixed(2)}% spread between ${opportunity.exchanges.join(' ↔ ')}`);
  }
}

export const notificationManager = new NotificationManager();
