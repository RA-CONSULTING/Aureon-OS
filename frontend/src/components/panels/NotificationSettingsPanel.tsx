import { useState } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Button } from '@/components/ui/button';
import { Switch } from '@/components/ui/switch';
import { Label } from '@/components/ui/label';
import { notificationManager } from '@/core/notificationManager';
import { Bell, MessageSquare, Send } from 'lucide-react';
import { toast } from '@/hooks/use-toast';

export const NotificationSettingsPanel = () => {
  const [telegramBotToken, setTelegramBotToken] = useState('');
  const [telegramChatId, setTelegramChatId] = useState('');
  const [discordWebhook, setDiscordWebhook] = useState('');
  const [enableTelegram, setEnableTelegram] = useState(false);
  const [enableDiscord, setEnableDiscord] = useState(false);
  const [isSaving, setIsSaving] = useState(false);

  const handleSave = async () => {
    setIsSaving(true);
    try {
      notificationManager.configure({
        telegramEnabled: enableTelegram,
        telegramBotToken: enableTelegram ? telegramBotToken : undefined,
        telegramChatId: enableTelegram ? telegramChatId : undefined,
        discordEnabled: enableDiscord,
        discordWebhookUrl: enableDiscord ? discordWebhook : undefined
      });
      
      toast({
        title: "Settings Saved",
        description: "Notification settings have been updated"
      });
    } finally {
      setIsSaving(false);
    }
  };

  const handleTestTelegram = async () => {
    await notificationManager.notify('INFO', 'Test Notification', 
      '🧪 Test notification from AUREON Trading System');
    toast({
      title: "Test Sent",
      description: "Check your Telegram if configured"
    });
  };

  const handleTestDiscord = async () => {
    await notificationManager.notify('INFO', 'Test Notification',
      '🧪 Test notification from AUREON Trading System');
    toast({
      title: "Test Sent", 
      description: "Check your Discord if configured"
    });
  };

  return (
    <Card className="border-border/50 bg-card/50 backdrop-blur">
      <CardHeader className="pb-3">
        <CardTitle className="flex items-center gap-2 text-sm font-medium">
          <Bell className="h-4 w-4 text-primary" />
          Notification Settings
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        {/* Telegram Section */}
        <div className="space-y-3 p-3 rounded-lg bg-muted/20">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <Send className="h-4 w-4 text-primary" />
              <Label className="text-sm font-medium">Telegram</Label>
            </div>
            <Switch 
              checked={enableTelegram} 
              onCheckedChange={setEnableTelegram}
            />
          </div>
          
          {enableTelegram && (
            <div className="space-y-2">
              <Input
                placeholder="Bot Token"
                value={telegramBotToken}
                onChange={(e) => setTelegramBotToken(e.target.value)}
                className="h-8 text-xs"
              />
              <Input
                placeholder="Chat ID"
                value={telegramChatId}
                onChange={(e) => setTelegramChatId(e.target.value)}
                className="h-8 text-xs"
              />
              <Button 
                variant="outline" 
                size="sm" 
                className="w-full h-7 text-xs"
                onClick={handleTestTelegram}
              >
                Send Test
              </Button>
            </div>
          )}
        </div>

        {/* Discord Section */}
        <div className="space-y-3 p-3 rounded-lg bg-muted/20">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <MessageSquare className="h-4 w-4 text-primary" />
              <Label className="text-sm font-medium">Discord</Label>
            </div>
            <Switch 
              checked={enableDiscord} 
              onCheckedChange={setEnableDiscord}
            />
          </div>
          
          {enableDiscord && (
            <div className="space-y-2">
              <Input
                placeholder="Webhook URL"
                value={discordWebhook}
                onChange={(e) => setDiscordWebhook(e.target.value)}
                className="h-8 text-xs"
              />
              <Button 
                variant="outline" 
                size="sm" 
                className="w-full h-7 text-xs"
                onClick={handleTestDiscord}
              >
                Send Test
              </Button>
            </div>
          )}
        </div>

        <Button 
          className="w-full h-8 text-xs" 
          onClick={handleSave}
          disabled={isSaving}
        >
          {isSaving ? 'Saving...' : 'Save Settings'}
        </Button>
      </CardContent>
    </Card>
  );
};
