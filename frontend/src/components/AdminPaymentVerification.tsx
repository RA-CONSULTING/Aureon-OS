import { useState, useEffect } from "react";
import { supabase } from "@/integrations/supabase/client";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { useToast } from "@/hooks/use-toast";
import { Loader2, CheckCircle2, XCircle, Clock, Euro } from "lucide-react";
import { Alert, AlertDescription } from "@/components/ui/alert";

interface PaymentTransaction {
  id: string;
  user_id: string;
  amount: number;
  currency: string;
  payment_status: string;
  created_at: string;
  paid_at: string | null;
  profiles: {
    full_name: string;
    email: string;
  };
}

export default function AdminPaymentVerification() {
  const { toast } = useToast();
  const [loading, setLoading] = useState(true);
  const [verifying, setVerifying] = useState<string | null>(null);
  const [transactions, setTransactions] = useState<PaymentTransaction[]>([]);

  useEffect(() => {
    loadPendingPayments();
    
    // Subscribe to real-time updates
    const channel = supabase
      .channel('payment_changes')
      .on(
        'postgres_changes',
        {
          event: '*',
          schema: 'public',
          table: 'payment_transactions'
        },
        () => {
          loadPendingPayments();
        }
      )
      .subscribe();

    return () => {
      supabase.removeChannel(channel);
    };
  }, []);

  const loadPendingPayments = async () => {
    try {
      const { data, error } = await supabase
        .from('payment_transactions')
        .select(`
          *,
          profiles:user_id (
            full_name,
            email
          )
        `)
        .order('created_at', { ascending: false })
        .limit(50);

      if (error) throw error;

      setTransactions(data as any || []);
    } catch (error) {
      console.error('Error loading payments:', error);
      toast({
        title: "Error",
        description: "Failed to load payment transactions",
        variant: "destructive",
      });
    } finally {
      setLoading(false);
    }
  };

  const handleVerifyPayment = async (userId: string, transactionId: string) => {
    setVerifying(transactionId);
    try {
      const { data: { session } } = await supabase.auth.getSession();
      if (!session) throw new Error('Not authenticated');

      const { error } = await supabase.functions.invoke('verify-payment', {
        body: { userId, transactionId },
        headers: {
          Authorization: `Bearer ${session.access_token}`
        }
      });

      if (error) throw error;

      toast({
        title: "Success",
        description: "Payment verified successfully",
      });

      loadPendingPayments();
    } catch (error) {
      console.error('Error verifying payment:', error);
      toast({
        title: "Error",
        description: error instanceof Error ? error.message : "Failed to verify payment",
        variant: "destructive",
      });
    } finally {
      setVerifying(null);
    }
  };

  const getStatusBadge = (status: string) => {
    switch (status) {
      case 'completed':
        return <Badge className="bg-success"><CheckCircle2 className="w-3 h-3 mr-1" />Completed</Badge>;
      case 'pending':
        return <Badge variant="secondary"><Clock className="w-3 h-3 mr-1" />Pending</Badge>;
      case 'failed':
        return <Badge variant="destructive"><XCircle className="w-3 h-3 mr-1" />Failed</Badge>;
      default:
        return <Badge variant="outline">{status}</Badge>;
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center p-8">
        <Loader2 className="w-8 h-8 animate-spin text-primary" />
      </div>
    );
  }

  const pendingCount = transactions.filter(t => t.payment_status === 'pending').length;

  return (
    <div className="space-y-6">
      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <div>
              <CardTitle className="flex items-center gap-2">
                <Euro className="w-5 h-5" />
                Payment Verification
              </CardTitle>
              <CardDescription>
                Review and verify user payment transactions
              </CardDescription>
            </div>
            {pendingCount > 0 && (
              <Badge variant="secondary" className="text-lg px-3 py-1">
                {pendingCount} Pending
              </Badge>
            )}
          </div>
        </CardHeader>
        <CardContent>
          <Alert className="mb-4">
            <AlertDescription>
              After users complete payment via SumUp, manually verify transactions here to grant platform access.
            </AlertDescription>
          </Alert>

          {transactions.length === 0 ? (
            <div className="text-center py-8 text-muted-foreground">
              No payment transactions found
            </div>
          ) : (
            <div className="border rounded-lg overflow-hidden">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>User</TableHead>
                    <TableHead>Email</TableHead>
                    <TableHead>Amount</TableHead>
                    <TableHead>Status</TableHead>
                    <TableHead>Created</TableHead>
                    <TableHead>Paid At</TableHead>
                    <TableHead className="text-right">Action</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {transactions.map((transaction) => (
                    <TableRow key={transaction.id}>
                      <TableCell className="font-medium">
                        {transaction.profiles?.full_name || 'N/A'}
                      </TableCell>
                      <TableCell>{transaction.profiles?.email || 'N/A'}</TableCell>
                      <TableCell>
                        {transaction.currency} {transaction.amount.toFixed(2)}
                      </TableCell>
                      <TableCell>{getStatusBadge(transaction.payment_status)}</TableCell>
                      <TableCell>
                        {new Date(transaction.created_at).toLocaleDateString()}
                      </TableCell>
                      <TableCell>
                        {transaction.paid_at 
                          ? new Date(transaction.paid_at).toLocaleDateString()
                          : '-'
                        }
                      </TableCell>
                      <TableCell className="text-right">
                        {transaction.payment_status === 'pending' ? (
                          <Button
                            onClick={() => handleVerifyPayment(transaction.user_id, transaction.id)}
                            disabled={verifying === transaction.id}
                            size="sm"
                          >
                            {verifying === transaction.id ? (
                              <>
                                <Loader2 className="w-3 h-3 mr-1 animate-spin" />
                                Verifying...
                              </>
                            ) : (
                              <>
                                <CheckCircle2 className="w-3 h-3 mr-1" />
                                Verify
                              </>
                            )}
                          </Button>
                        ) : (
                          <span className="text-sm text-muted-foreground">
                            {transaction.payment_status === 'completed' ? 'Verified' : '-'}
                          </span>
                        )}
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
