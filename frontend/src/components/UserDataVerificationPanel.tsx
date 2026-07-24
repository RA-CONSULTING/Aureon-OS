import React from 'react';
import { useUserDataVerification } from '@/hooks/useUserDataVerification';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Shield, ShieldCheck, ShieldAlert, RefreshCw, User, Key, Database, Activity } from 'lucide-react';

export function UserDataVerificationPanel() {
  const {
    userId,
    userEmail,
    sessionCreatedAt,
    isAuthenticated,
    isOwnData,
    exchanges,
    dataSources,
    overallStatus,
    lastFullVerification,
    isVerifying,
    verify,
  } = useUserDataVerification();

  const getStatusIcon = () => {
    switch (overallStatus) {
      case 'VERIFIED':
        return <ShieldCheck className="h-5 w-5 text-success" />;
      case 'PARTIAL':
        return <Shield className="h-5 w-5 text-warning" />;
      default:
        return <ShieldAlert className="h-5 w-5 text-destructive" />;
    }
  };

  const getStatusBadge = (status: string) => {
    switch (status) {
      case 'VERIFIED':
      case 'LIVE':
        return <Badge className="bg-success/20 text-success border-success/30">✓ {status}</Badge>;
      case 'PARTIAL':
      case 'STALE':
        return <Badge className="bg-warning/20 text-warning border-warning/30">⚠ {status}</Badge>;
      case 'UNVERIFIED':
      case 'NO_DATA':
      case 'DEMO':
        return <Badge className="bg-destructive/20 text-destructive border-destructive/30">✗ {status}</Badge>;
      default:
        return <Badge variant="outline">{status}</Badge>;
    }
  };

  const formatDate = (dateStr: string | null) => {
    if (!dateStr) return 'Never';
    return new Date(dateStr).toLocaleString();
  };

  return (
    <Card className="bg-card/80 backdrop-blur border-border/50">
      <CardHeader className="pb-3">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            {getStatusIcon()}
            <CardTitle className="text-lg">Data Verification</CardTitle>
          </div>
          <div className="flex items-center gap-2">
            {getStatusBadge(overallStatus)}
            <Button
              variant="ghost"
              size="sm"
              onClick={verify}
              disabled={isVerifying}
              className="h-8 w-8 p-0"
            >
              <RefreshCw className={`h-4 w-4 ${isVerifying ? 'animate-spin' : ''}`} />
            </Button>
          </div>
        </div>
      </CardHeader>
      
      <CardContent className="space-y-4">
        {/* Identity Section */}
        <div className="space-y-2">
          <div className="flex items-center gap-2 text-sm font-medium text-muted-foreground">
            <User className="h-4 w-4" />
            Identity
          </div>
          <div className="bg-muted/30 rounded-lg p-3 space-y-1.5">
            <div className="flex justify-between text-sm">
              <span className="text-muted-foreground">Email:</span>
              <span className="font-mono">{userEmail || 'Not authenticated'}</span>
            </div>
            <div className="flex justify-between text-sm">
              <span className="text-muted-foreground">User ID:</span>
              <span className="font-mono text-xs">
                {userId ? `${userId.slice(0, 8)}...${userId.slice(-4)}` : 'N/A'}
              </span>
            </div>
            <div className="flex justify-between text-sm">
              <span className="text-muted-foreground">Session Started:</span>
              <span className="text-xs">{formatDate(sessionCreatedAt)}</span>
            </div>
            <div className="flex justify-between text-sm">
              <span className="text-muted-foreground">Data Ownership:</span>
              {isOwnData ? (
                <Badge className="bg-success/20 text-success border-success/30 text-xs">
                  ✓ YOUR DATA
                </Badge>
              ) : (
                <Badge className="bg-destructive/20 text-destructive border-destructive/30 text-xs">
                  ✗ UNVERIFIED
                </Badge>
              )}
            </div>
          </div>
        </div>

        {/* Exchange Credentials Section */}
        <div className="space-y-2">
          <div className="flex items-center gap-2 text-sm font-medium text-muted-foreground">
            <Key className="h-4 w-4" />
            Exchange Credentials
          </div>
          <div className="bg-muted/30 rounded-lg p-3 space-y-2">
            {exchanges.map((ex) => (
              <div key={ex.exchange} className="flex items-center justify-between text-sm">
                <div className="flex items-center gap-2">
                  <span className={ex.hasCredentials ? 'text-foreground' : 'text-muted-foreground'}>
                    {ex.exchange}
                  </span>
                  {ex.partialApiKey && (
                    <span className="font-mono text-xs text-muted-foreground">
                      {ex.partialApiKey}
                    </span>
                  )}
                </div>
                {getStatusBadge(ex.status)}
              </div>
            ))}
          </div>
        </div>

        {/* Data Sources Section */}
        <div className="space-y-2">
          <div className="flex items-center gap-2 text-sm font-medium text-muted-foreground">
            <Database className="h-4 w-4" />
            Data Sources
          </div>
          <div className="bg-muted/30 rounded-lg p-3 space-y-2">
            {dataSources.map((ds) => (
              <div key={ds.source} className="flex items-center justify-between text-sm">
                <div className="flex items-center gap-2">
                  <span className={ds.status === 'LIVE' ? 'text-foreground' : 'text-muted-foreground'}>
                    {ds.source}
                  </span>
                  {ds.value !== null && (
                    <span className="font-mono text-xs text-muted-foreground">
                      {typeof ds.value === 'number' ? ds.value.toFixed(4) : ds.value}
                    </span>
                  )}
                </div>
                {getStatusBadge(ds.status)}
              </div>
            ))}
          </div>
        </div>

        {/* Verification Footer */}
        <div className="flex items-center justify-between text-xs text-muted-foreground pt-2 border-t border-border/50">
          <div className="flex items-center gap-1">
            <Activity className="h-3 w-3" />
            Last verified: {formatDate(lastFullVerification)}
          </div>
          <Button variant="link" size="sm" onClick={verify} className="h-auto p-0 text-xs">
            Verify Now
          </Button>
        </div>
      </CardContent>
    </Card>
  );
}
