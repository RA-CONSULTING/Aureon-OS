import { useState, useEffect } from "react";
import { supabase } from "@/integrations/supabase/client";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Loader2, CreditCard, CheckCircle2, ExternalLink } from "lucide-react";
import { toast } from "sonner";

interface PaymentGateProps {
  userId: string;
  onPaymentComplete: () => void;
}

export default function PaymentGate({ userId, onPaymentComplete }: PaymentGateProps) {
  const [loading, setLoading] = useState(false);
  const [paymentStatus, setPaymentStatus] = useState<string>("pending");
  const [paymentUrl] = useState("https://pay.sumup.com/b2c/");

  useEffect(() => {
    checkPaymentStatus();
  }, [userId]);

  const checkPaymentStatus = async () => {
    try {
      const { data: profile } = await supabase
        .from("profiles")
        .select("payment_completed")
        .eq("id", userId)
        .single();

      if (profile?.payment_completed) {
        setPaymentStatus("completed");
        onPaymentComplete();
      }
    } catch (error) {
      console.error("Error checking payment status:", error);
    }
  };

  const handleProceedToPayment = async () => {
    setLoading(true);
    try {
      // Create payment transaction record
      const { data: transaction, error: transactionError } = await supabase
        .from("payment_transactions")
        .insert({
          user_id: userId,
          amount: 100.00,
          currency: "GBP",
          payment_provider: "sumup",
          payment_status: "pending",
          payment_url: paymentUrl,
          metadata: {
            purpose: "signup_fee",
            created_from: "payment_gate",
            total_amount: 100.00,
            platform_amount: 90.00,
            charity_amount: 10.00,
            charity_percentage: 10
          }
        })
        .select()
        .single();

      if (transactionError) throw transactionError;

      // Log to audit
      await supabase
        .from("data_access_audit")
        .insert({
          user_id: userId,
          accessed_by: userId,
          access_type: "CREATE",
          resource_type: "PAYMENT_INITIATION",
          metadata: {
            transaction_id: transaction.id,
            amount: 100.00,
            timestamp: new Date().toISOString()
          }
        });

      toast.success("Redirecting to payment...");
      
      // Open SumUp payment page
      window.open(paymentUrl, "_blank");
      
      // Start polling for payment completion
      startPaymentPolling();

    } catch (error) {
      console.error("Payment initiation error:", error);
      toast.error("Failed to initiate payment. Please try again.");
    } finally {
      setLoading(false);
    }
  };

  const startPaymentPolling = () => {
    const pollInterval = setInterval(async () => {
      await checkPaymentStatus();
      
      // Stop polling if payment completed
      const { data: profile } = await supabase
        .from("profiles")
        .select("payment_completed")
        .eq("id", userId)
        .single();

      if (profile?.payment_completed) {
        clearInterval(pollInterval);
        setPaymentStatus("completed");
        toast.success("Payment verified! Welcome to AUREON Trading Platform!");
        onPaymentComplete();
      }
    }, 5000); // Check every 5 seconds

    // Stop polling after 10 minutes
    setTimeout(() => clearInterval(pollInterval), 600000);
  };

  const handleManualVerification = () => {
    toast.info("Please contact support if you've completed payment but it's not showing as verified.");
  };

  if (paymentStatus === "completed") {
    return (
      <Card className="max-w-md mx-auto">
        <CardHeader>
          <div className="flex items-center gap-2">
            <CheckCircle2 className="w-6 h-6 text-success" />
            <CardTitle>Payment Verified</CardTitle>
          </div>
          <CardDescription>
            Your payment has been confirmed. Redirecting to dashboard...
          </CardDescription>
        </CardHeader>
      </Card>
    );
  }

  return (
    <Card className="max-w-md mx-auto">
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <CreditCard className="w-6 h-6" />
          Complete Your Registration
        </CardTitle>
        <CardDescription>
          One-time signup fee to access the AUREON Quantum Trading System
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-6">
        <div className="p-6 bg-gradient-to-br from-primary/10 to-primary/5 rounded-lg border border-primary/20">
          <div className="text-center mb-4">
            <p className="text-sm text-muted-foreground mb-2">Registration Fee</p>
            <p className="text-4xl font-bold text-primary">£100.00</p>
            <p className="text-xs text-muted-foreground mt-1">One-time payment</p>
          </div>
          
          <div className="mb-4 p-3 bg-success/10 border border-success/20 rounded-lg">
            <div className="flex items-center justify-between text-sm">
              <span className="text-success dark:text-success font-medium">💚 Charitable Contribution</span>
              <span className="font-bold text-success dark:text-success">£10.00</span>
            </div>
            <p className="text-xs text-success dark:text-success mt-1">
              10% of your payment supports charitable causes
            </p>
          </div>

          <div className="space-y-2 text-sm">
            <div className="flex items-center gap-2">
              <CheckCircle2 className="w-4 h-4 text-success" />
              <span>Full access to AUREON trading system</span>
            </div>
            <div className="flex items-center gap-2">
              <CheckCircle2 className="w-4 h-4 text-success" />
              <span>Real-time market analysis & signals</span>
            </div>
            <div className="flex items-center gap-2">
              <CheckCircle2 className="w-4 h-4 text-success" />
              <span>Portfolio management tools</span>
            </div>
            <div className="flex items-center gap-2">
              <CheckCircle2 className="w-4 h-4 text-success" />
              <span>Priority KYC verification</span>
            </div>
          </div>
        </div>

        <Alert>
          <AlertDescription className="text-sm">
            You'll be redirected to SumUp's secure payment page. After completing payment, 
            return to this page for automatic verification.
          </AlertDescription>
        </Alert>

        <div className="space-y-3">
          <Button
            onClick={handleProceedToPayment}
            disabled={loading}
            className="w-full"
            size="lg"
          >
            {loading ? (
              <>
                <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                Processing...
              </>
            ) : (
              <>
                <ExternalLink className="w-4 h-4 mr-2" />
                Proceed to Payment
              </>
            )}
          </Button>

          <Button
            variant="outline"
            onClick={handleManualVerification}
            className="w-full"
            size="sm"
          >
            Already Paid? Contact Support
          </Button>
        </div>

        <p className="text-xs text-center text-muted-foreground">
          Secure payment powered by SumUp. Your payment information is encrypted and secure.
        </p>
      </CardContent>
    </Card>
  );
}
