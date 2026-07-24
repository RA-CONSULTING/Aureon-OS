import { Card, CardContent } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { useGasTank } from '@/hooks/useGasTank';
import { useState } from 'react';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';

interface GasTankDisplayProps {
  userId: string | null;
  onEmpty?: () => void;
}

export const GasTankDisplay = ({ userId, onEmpty }: GasTankDisplayProps) => {
  const gasTank = useGasTank(userId);
  const [showTopUpModal, setShowTopUpModal] = useState(false);
  const [topUpAmount, setTopUpAmount] = useState('100');
  const [isTopping, setIsTopping] = useState(false);

  // Calculate percentage for fuel gauge
  const percentage = gasTank.initialBalance > 0 
    ? Math.max(0, Math.min(100, (gasTank.balance / gasTank.initialBalance) * 100))
    : 0;

  // Determine gauge color
  const getGaugeColor = () => {
    if (gasTank.status === 'EMPTY') return 'from-gray-600 to-gray-800';
    if (gasTank.status === 'CRITICAL') return 'from-destructive to-destructive';
    if (gasTank.status === 'LOW') return 'from-warning to-warning';
    return 'from-success to-success';
  };

  // Determine status emoji
  const getStatusEmoji = () => {
    if (gasTank.status === 'EMPTY') return '';
    if (gasTank.status === 'CRITICAL') return '';
    if (gasTank.status === 'LOW') return '';
    return '';
  };

  const handleTopUp = async () => {
    const amount = parseFloat(topUpAmount);
    if (isNaN(amount) || amount < 10 || amount > 10000) {
      return;
    }

    setIsTopping(true);
    const result = await gasTank.topUp(amount, gasTank.membershipType);
    setIsTopping(false);

    if (result.success) {
      setShowTopUpModal(false);
      setTopUpAmount('100');
    }
  };

  if (gasTank.isLoading) {
    return (
      <Card className="bg-card/50 backdrop-blur border-primary/20">
        <CardContent className="p-4">
          <div className="flex items-center justify-center">
            <p className="text-sm text-muted-foreground">Loading gas tank...</p>
          </div>
        </CardContent>
      </Card>
    );
  }

  return (
    <>
      <Card className={`bg-card/50 backdrop-blur border-primary/20 relative ${
        gasTank.status === 'LOW' || gasTank.status === 'CRITICAL' ? 'animate-pulse' : ''
      }`}>
        <CardContent className="p-4">
          <div className="space-y-3">
            {/* Header */}
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <span className="text-xl"></span>
                <h3 className="font-bold text-sm">GAS TANK</h3>
              </div>
              <div className="flex items-center gap-2">
                <span className="text-xs font-mono bg-primary/10 px-2 py-1 rounded">
                  {gasTank.membershipType.toUpperCase()} {(gasTank.feeRate * 100).toFixed(0)}%
                </span>
              </div>
            </div>

            {/* Fuel Gauge */}
            <div className="space-y-1">
              <div className="h-8 bg-muted/30 rounded-lg overflow-hidden relative">
                <div
                  className={`h-full bg-gradient-to-r ${getGaugeColor()} transition-all duration-500`}
                  style={{ width: `${percentage}%` }}
                />
                <div className="absolute inset-0 flex items-center justify-center">
                  <span className="text-xs font-bold text-white drop-shadow-lg">
                    {percentage.toFixed(0)}%
                  </span>
                </div>
              </div>
              <div className="flex items-center justify-between text-xs">
                <span className="text-muted-foreground">
                  £{gasTank.balance.toFixed(2)} / £{gasTank.initialBalance.toFixed(2)}
                </span>
              </div>
            </div>

            {/* Metrics Grid */}
            <div className="grid grid-cols-2 gap-2 text-xs">
              <div>
                <p className="text-muted-foreground">High-Water Mark</p>
                <p className="font-bold">£{gasTank.highWaterMark.toFixed(2)}</p>
              </div>
              <div>
                <p className="text-muted-foreground">Today's Fees</p>
                <p className="font-bold text-destructive">£{gasTank.feesPaidToday.toFixed(2)}</p>
              </div>
              <div>
                <p className="text-muted-foreground">Total Fees Paid</p>
                <p className="font-bold text-destructive">£{gasTank.totalFeesPaid.toFixed(2)}</p>
              </div>
              <div>
                <p className="text-muted-foreground">Status</p>
                <p className="font-bold">
                  {getStatusEmoji()} {gasTank.status}
                </p>
              </div>
            </div>

            {/* Top Up Button */}
            <Button
              onClick={() => setShowTopUpModal(true)}
              className="w-full bg-gradient-to-r from-primary to-primary/80"
              size="sm"
            >
               Top Up
            </Button>

            {/* Empty Overlay */}
            {gasTank.status === 'EMPTY' && (
              <div className="absolute inset-0 bg-black/80 backdrop-blur-sm flex items-center justify-center rounded-lg">
                <div className="text-center p-4">
                  <p className="text-2xl mb-2"></p>
                  <p className="font-bold text-destructive mb-2">GAS TANK EMPTY</p>
                  <p className="text-xs text-muted-foreground mb-3">Trading Paused</p>
                  <Button
                    onClick={() => setShowTopUpModal(true)}
                    variant="destructive"
                    size="sm"
                  >
                    Top Up Now
                  </Button>
                </div>
              </div>
            )}
          </div>
        </CardContent>
      </Card>

      {/* Top-Up Modal */}
      <Dialog open={showTopUpModal} onOpenChange={setShowTopUpModal}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle> Top Up Gas Tank</DialogTitle>
            <DialogDescription>
              Add credits to your gas tank to continue trading
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-4">
            <div>
              <Label htmlFor="amount">Amount (£)</Label>
              <Input
                id="amount"
                type="number"
                min="10"
                max="10000"
                step="10"
                value={topUpAmount}
                onChange={(e) => setTopUpAmount(e.target.value)}
                placeholder="100"
              />
              <p className="text-xs text-muted-foreground mt-1">
                Min: £10 | Max: £10,000
              </p>
            </div>

            <div className="bg-muted/30 p-3 rounded-lg space-y-2 text-sm">
              <div className="flex justify-between">
                <span>Membership Type:</span>
                <span className="font-bold">{gasTank.membershipType.toUpperCase()}</span>
              </div>
              <div className="flex justify-between">
                <span>Performance Fee:</span>
                <span className="font-bold">{(gasTank.feeRate * 100).toFixed(0)}%</span>
              </div>
              <p className="text-xs text-muted-foreground">
                Fees are only charged on NEW profits above your high-water mark
              </p>
            </div>

            <div className="flex gap-2">
              <Button
                onClick={() => setShowTopUpModal(false)}
                variant="outline"
                className="flex-1"
                disabled={isTopping}
              >
                Cancel
              </Button>
              <Button
                onClick={handleTopUp}
                className="flex-1 bg-gradient-to-r from-primary to-primary/80"
                disabled={isTopping}
              >
                {isTopping ? 'Processing...' : 'Top Up'}
              </Button>
            </div>
          </div>
        </DialogContent>
      </Dialog>
    </>
  );
};
