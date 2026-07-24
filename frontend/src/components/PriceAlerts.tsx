import { useState } from 'react';
import { Card } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Switch } from '@/components/ui/switch';
import { usePriceAlerts } from '@/hooks/usePriceAlerts';
import { Bell, BellOff, Trash2, Plus, TrendingUp, TrendingDown } from 'lucide-react';
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle, DialogTrigger } from '@/components/ui/dialog';
import type { WatchlistSymbol } from '@/hooks/useMultiSymbolWatchlist';

const AVAILABLE_SYMBOLS = [
  // TOP TIER
  'BTCUSDT', 'ETHUSDT', 'BNBUSDT', 'SOLUSDT', 'XRPUSDT', 'ADAUSDT', 'AVAXUSDT',
  'DOTUSDT', 'ATOMUSDT', 'NEARUSDT', 'APTUSDT', 'SUIUSDT',
  // LAYER 2s
  'ARBUSDT', 'OPUSDT', 'MATICUSDT',
  // DEFI
  'UNIUSDT', 'AAVEUSDT', 'LINKUSDT',
  // AI
  'FETUSDT', 'INJUSDT', 'WLDUSDT',
  // MEMECOINS
  'DOGEUSDT', 'SHIBUSDT', 'PEPEUSDT', 'BONKUSDT', 'WIFUSDT',
];

type PriceAlertsProps = {
  symbolData: Map<string, WatchlistSymbol>;
};

export const PriceAlerts = ({ symbolData }: PriceAlertsProps) => {
  const { alerts, loading, createAlert, deleteAlert, toggleAlert } = usePriceAlerts(symbolData);
  const [isDialogOpen, setIsDialogOpen] = useState(false);
  const [formData, setFormData] = useState({
    symbol: 'BTCUSDT',
    alertType: 'price_above' as const,
    targetValue: '',
    notes: '',
  });

  const handleCreateAlert = async () => {
    if (!formData.targetValue) return;

    const success = await createAlert(
      formData.symbol,
      formData.alertType,
      parseFloat(formData.targetValue),
      formData.notes || undefined
    );

    if (success) {
      setIsDialogOpen(false);
      setFormData({
        symbol: 'BTCUSDT',
        alertType: 'price_above',
        targetValue: '',
        notes: '',
      });
    }
  };

  const getAlertTypeLabel = (type: string) => {
    switch (type) {
      case 'price_above': return 'Price Above';
      case 'price_below': return 'Price Below';
      case 'change_percent_above': return 'Gain Above';
      case 'change_percent_below': return 'Loss Below';
      default: return type;
    }
  };

  const getAlertIcon = (type: string) => {
    return type.includes('above') ? <TrendingUp className="h-4 w-4" /> : <TrendingDown className="h-4 w-4" />;
  };

  const activeAlerts = alerts.filter(a => a.is_active && !a.is_triggered);
  const triggeredAlerts = alerts.filter(a => a.is_triggered);

  return (
    <Card className="p-6">
      <div className="flex items-center justify-between mb-4">
        <div>
          <h3 className="text-lg font-semibold">Price Alerts</h3>
          <p className="text-sm text-muted-foreground">
            Get notified when prices reach your targets
          </p>
        </div>
        <Dialog open={isDialogOpen} onOpenChange={setIsDialogOpen}>
          <DialogTrigger asChild>
            <Button size="sm">
              <Plus className="h-4 w-4 mr-2" />
              New Alert
            </Button>
          </DialogTrigger>
          <DialogContent>
            <DialogHeader>
              <DialogTitle>Create Price Alert</DialogTitle>
              <DialogDescription>
                Set up a notification for when a symbol reaches your target
              </DialogDescription>
            </DialogHeader>
            
            <div className="space-y-4 py-4">
              <div className="space-y-2">
                <Label htmlFor="symbol">Symbol</Label>
                <Select
                  value={formData.symbol}
                  onValueChange={(value) => setFormData({ ...formData, symbol: value })}
                >
                  <SelectTrigger id="symbol">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    {AVAILABLE_SYMBOLS.map(symbol => (
                      <SelectItem key={symbol} value={symbol}>{symbol}</SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>

              <div className="space-y-2">
                <Label htmlFor="alertType">Alert Type</Label>
                <Select
                  value={formData.alertType}
                  onValueChange={(value: any) => setFormData({ ...formData, alertType: value })}
                >
                  <SelectTrigger id="alertType">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="price_above">Price Above</SelectItem>
                    <SelectItem value="price_below">Price Below</SelectItem>
                    <SelectItem value="change_percent_above">24h Gain Above %</SelectItem>
                    <SelectItem value="change_percent_below">24h Loss Below %</SelectItem>
                  </SelectContent>
                </Select>
              </div>

              <div className="space-y-2">
                <Label htmlFor="targetValue">
                  Target Value {formData.alertType.includes('percent') ? '(%)' : '($)'}
                </Label>
                <Input
                  id="targetValue"
                  type="number"
                  step="0.01"
                  value={formData.targetValue}
                  onChange={(e) => setFormData({ ...formData, targetValue: e.target.value })}
                  placeholder={formData.alertType.includes('percent') ? '5.0' : '50000'}
                />
              </div>

              <div className="space-y-2">
                <Label htmlFor="notes">Notes (optional)</Label>
                <Input
                  id="notes"
                  value={formData.notes}
                  onChange={(e) => setFormData({ ...formData, notes: e.target.value })}
                  placeholder="Reminder or strategy notes"
                />
              </div>
            </div>

            <DialogFooter>
              <Button variant="outline" onClick={() => setIsDialogOpen(false)}>
                Cancel
              </Button>
              <Button onClick={handleCreateAlert} disabled={!formData.targetValue}>
                Create Alert
              </Button>
            </DialogFooter>
          </DialogContent>
        </Dialog>
      </div>

      {loading ? (
        <p className="text-sm text-muted-foreground">Loading alerts...</p>
      ) : (
        <div className="space-y-4">
          {/* Active Alerts */}
          {activeAlerts.length > 0 && (
            <div>
              <h4 className="text-sm font-medium mb-2">Active Alerts ({activeAlerts.length})</h4>
              <div className="space-y-2">
                {activeAlerts.map(alert => (
                  <Card key={alert.id} className="p-3 bg-muted/30">
                    <div className="flex items-start justify-between">
                      <div className="flex-1">
                        <div className="flex items-center gap-2 mb-1">
                          {getAlertIcon(alert.alert_type)}
                          <span className="font-semibold text-sm">{alert.symbol}</span>
                          <Badge variant="outline" className="text-xs">
                            {getAlertTypeLabel(alert.alert_type)}
                          </Badge>
                        </div>
                        <p className="text-sm text-muted-foreground">
                          Target: {alert.alert_type.includes('percent') ? `${alert.target_value}%` : `$${alert.target_value.toLocaleString()}`}
                        </p>
                        {alert.notes && (
                          <p className="text-xs text-muted-foreground mt-1">{alert.notes}</p>
                        )}
                      </div>
                      <div className="flex items-center gap-2">
                        <Switch
                          checked={alert.is_active}
                          onCheckedChange={(checked) => toggleAlert(alert.id, checked)}
                        />
                        <Button
                          size="sm"
                          variant="ghost"
                          onClick={() => deleteAlert(alert.id)}
                        >
                          <Trash2 className="h-4 w-4" />
                        </Button>
                      </div>
                    </div>
                  </Card>
                ))}
              </div>
            </div>
          )}

          {/* Triggered Alerts */}
          {triggeredAlerts.length > 0 && (
            <div>
              <h4 className="text-sm font-medium mb-2">Triggered ({triggeredAlerts.length})</h4>
              <div className="space-y-2">
                {triggeredAlerts.map(alert => (
                  <Card key={alert.id} className="p-3 bg-success/10 border-success/20">
                    <div className="flex items-start justify-between">
                      <div className="flex-1">
                        <div className="flex items-center gap-2 mb-1">
                          <Bell className="h-4 w-4 text-success" />
                          <span className="font-semibold text-sm">{alert.symbol}</span>
                          <Badge className="text-xs bg-success">Triggered</Badge>
                        </div>
                        <p className="text-sm">
                          Target: {alert.alert_type.includes('percent') ? `${alert.target_value}%` : `$${alert.target_value.toLocaleString()}`}
                          {alert.current_value && ` → Current: $${alert.current_value.toLocaleString()}`}
                        </p>
                        {alert.triggered_at && (
                          <p className="text-xs text-muted-foreground mt-1">
                            {new Date(alert.triggered_at).toLocaleString()}
                          </p>
                        )}
                      </div>
                      <Button
                        size="sm"
                        variant="ghost"
                        onClick={() => deleteAlert(alert.id)}
                      >
                        <Trash2 className="h-4 w-4" />
                      </Button>
                    </div>
                  </Card>
                ))}
              </div>
            </div>
          )}

          {alerts.length === 0 && (
            <div className="text-center py-8">
              <BellOff className="h-12 w-12 mx-auto text-muted-foreground mb-2" />
              <p className="text-sm text-muted-foreground">No price alerts set</p>
              <p className="text-xs text-muted-foreground">Create your first alert to get started</p>
            </div>
          )}
        </div>
      )}
    </Card>
  );
};
