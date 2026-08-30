import { useEffect, useState } from "react";
import { supabase } from "@/integrations/supabase/client";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { Textarea } from "@/components/ui/textarea";
import { Label } from "@/components/ui/label";
import { toast } from "sonner";
import { CheckCircle, XCircle, Eye, FileText, Calendar, MapPin, User } from "lucide-react";

interface KYCApplication {
  id: string;
  email: string;
  full_name: string;
  date_of_birth: string;
  location: string;
  id_document_path: string;
  kyc_status: string;
  data_consent_given: boolean;
  data_consent_date: string;
  created_at: string;
}

export default function AdminKYCDashboard() {
  const [applications, setApplications] = useState<KYCApplication[]>([]);
  const [loading, setLoading] = useState(true);
  const [selectedApp, setSelectedApp] = useState<KYCApplication | null>(null);
  const [documentUrl, setDocumentUrl] = useState<string>("");
  const [rejectionReason, setRejectionReason] = useState("");
  const [actionLoading, setActionLoading] = useState(false);
  const [showRejectDialog, setShowRejectDialog] = useState(false);
  const [filter, setFilter] = useState<"pending" | "verified" | "rejected">("pending");

  useEffect(() => {
    fetchApplications();

    // Subscribe to real-time updates
    const channel = supabase
      .channel('kyc_updates')
      .on(
        'postgres_changes',
        {
          event: '*',
          schema: 'public',
          table: 'profiles',
        },
        () => {
          fetchApplications();
        }
      )
      .subscribe();

    return () => {
      supabase.removeChannel(channel);
    };
  }, [filter]);

  const fetchApplications = async () => {
    try {
      setLoading(true);
      const { data, error } = await supabase
        .from('profiles')
        .select('*')
        .eq('kyc_status', filter)
        .order('created_at', { ascending: false });

      if (error) throw error;
      setApplications(data || []);
    } catch (error) {
      console.error('Error fetching applications:', error);
      toast.error('Failed to load KYC applications');
    } finally {
      setLoading(false);
    }
  };

  const viewDocument = async (app: KYCApplication) => {
    try {
      if (!app.id_document_path) {
        toast.error('No document uploaded for this application');
        return;
      }

      const { data, error } = await supabase.storage
        .from('id-verification')
        .createSignedUrl(app.id_document_path, 3600); // 1 hour expiry

      if (error) throw error;
      
      setDocumentUrl(data.signedUrl);
      setSelectedApp(app);
    } catch (error) {
      console.error('Error loading document:', error);
      toast.error('Failed to load ID document');
    }
  };

  const handleApprove = async (app: KYCApplication) => {
    try {
      setActionLoading(true);

      const { error } = await supabase.functions.invoke('update-kyc-status', {
        body: {
          userId: app.id,
          status: 'verified',
          reason: 'KYC verification approved by admin'
        }
      });

      if (error) throw error;

      toast.success(`KYC approved for ${app.full_name}`);
      fetchApplications();
      setSelectedApp(null);
      setDocumentUrl("");
    } catch (error) {
      console.error('Error approving KYC:', error);
      toast.error('Failed to approve KYC');
    } finally {
      setActionLoading(false);
    }
  };

  const handleReject = async () => {
    if (!selectedApp) return;

    if (!rejectionReason.trim()) {
      toast.error('Please provide a rejection reason');
      return;
    }

    try {
      setActionLoading(true);

      const { error } = await supabase.functions.invoke('update-kyc-status', {
        body: {
          userId: selectedApp.id,
          status: 'rejected',
          reason: rejectionReason
        }
      });

      if (error) throw error;

      toast.success(`KYC rejected for ${selectedApp.full_name}`);
      fetchApplications();
      setSelectedApp(null);
      setDocumentUrl("");
      setShowRejectDialog(false);
      setRejectionReason("");
    } catch (error) {
      console.error('Error rejecting KYC:', error);
      toast.error('Failed to reject KYC');
    } finally {
      setActionLoading(false);
    }
  };

  const calculateAge = (dob: string) => {
    const birthDate = new Date(dob);
    const today = new Date();
    let age = today.getFullYear() - birthDate.getFullYear();
    const monthDiff = today.getMonth() - birthDate.getMonth();
    if (monthDiff < 0 || (monthDiff === 0 && today.getDate() < birthDate.getDate())) {
      age--;
    }
    return age;
  };

  const getStatusBadge = (status: string) => {
    switch (status) {
      case 'pending':
        return <Badge variant="outline" className="bg-warning/10 text-warning border-warning/20">Pending</Badge>;
      case 'verified':
        return <Badge variant="outline" className="bg-success/10 text-success border-success/20">Verified</Badge>;
      case 'rejected':
        return <Badge variant="outline" className="bg-destructive/10 text-destructive border-destructive/20">Rejected</Badge>;
      default:
        return <Badge variant="outline">{status}</Badge>;
    }
  };

  return (
    <div className="space-y-6">
      <Card>
        <CardHeader>
          <CardTitle>KYC Verification Dashboard</CardTitle>
          <CardDescription>
            Review and approve user identity verification applications
          </CardDescription>
        </CardHeader>
        <CardContent>
          <Tabs value={filter} onValueChange={(v) => setFilter(v as typeof filter)}>
            <TabsList className="grid w-full grid-cols-3 mb-6">
              <TabsTrigger value="pending">
                Pending ({applications.filter(a => a.kyc_status === 'pending').length})
              </TabsTrigger>
              <TabsTrigger value="verified">
                Verified ({applications.filter(a => a.kyc_status === 'verified').length})
              </TabsTrigger>
              <TabsTrigger value="rejected">
                Rejected ({applications.filter(a => a.kyc_status === 'rejected').length})
              </TabsTrigger>
            </TabsList>

            <TabsContent value={filter} className="space-y-4">
              {loading ? (
                <div className="text-center py-8 text-muted-foreground">
                  Loading applications...
                </div>
              ) : applications.length === 0 ? (
                <div className="text-center py-8 text-muted-foreground">
                  No {filter} applications found
                </div>
              ) : (
                applications.map((app) => (
                  <Card key={app.id} className="border-l-4 border-l-primary/20">
                    <CardContent className="pt-6">
                      <div className="flex items-start justify-between">
                        <div className="space-y-3 flex-1">
                          <div className="flex items-center gap-3">
                            <User className="w-5 h-5 text-muted-foreground" />
                            <div>
                              <p className="font-semibold">{app.full_name}</p>
                              <p className="text-sm text-muted-foreground">{app.email}</p>
                            </div>
                          </div>

                          <div className="grid grid-cols-2 gap-4 text-sm">
                            <div className="flex items-center gap-2">
                              <Calendar className="w-4 h-4 text-muted-foreground" />
                              <span>
                                {new Date(app.date_of_birth).toLocaleDateString()} 
                                <span className="text-muted-foreground ml-1">
                                  (Age: {calculateAge(app.date_of_birth)})
                                </span>
                              </span>
                            </div>

                            <div className="flex items-center gap-2">
                              <MapPin className="w-4 h-4 text-muted-foreground" />
                              <span>{app.location}</span>
                            </div>

                            <div className="col-span-2">
                              <span className="text-muted-foreground">Submitted: </span>
                              {new Date(app.created_at).toLocaleString()}
                            </div>

                            {app.data_consent_given && (
                              <div className="col-span-2 text-xs text-success">
                                ✓ Data consent given on {new Date(app.data_consent_date).toLocaleDateString()}
                              </div>
                            )}
                          </div>
                        </div>

                        <div className="flex flex-col gap-2 ml-4">
                          {getStatusBadge(app.kyc_status)}
                          
                          <Button
                            size="sm"
                            variant="outline"
                            onClick={() => viewDocument(app)}
                            disabled={!app.id_document_path}
                          >
                            <Eye className="w-4 h-4 mr-1" />
                            View ID
                          </Button>

                          {app.kyc_status === 'pending' && (
                            <>
                              <Button
                                size="sm"
                                variant="default"
                                onClick={() => handleApprove(app)}
                                disabled={actionLoading}
                              >
                                <CheckCircle className="w-4 h-4 mr-1" />
                                Approve
                              </Button>
                              <Button
                                size="sm"
                                variant="destructive"
                                onClick={() => {
                                  setSelectedApp(app);
                                  setShowRejectDialog(true);
                                }}
                                disabled={actionLoading}
                              >
                                <XCircle className="w-4 h-4 mr-1" />
                                Reject
                              </Button>
                            </>
                          )}
                        </div>
                      </div>
                    </CardContent>
                  </Card>
                ))
              )}
            </TabsContent>
          </Tabs>
        </CardContent>
      </Card>

      {/* Document Viewer Dialog */}
      <Dialog open={!!documentUrl} onOpenChange={(open) => !open && setDocumentUrl("")}>
        <DialogContent className="max-w-4xl max-h-[90vh]">
          <DialogHeader>
            <DialogTitle>ID Verification Document</DialogTitle>
            <DialogDescription>
              {selectedApp && (
                <>
                  {selectedApp.full_name} - {selectedApp.email}
                </>
              )}
            </DialogDescription>
          </DialogHeader>
          
          {documentUrl && (
            <div className="overflow-auto max-h-[70vh]">
              {documentUrl.endsWith('.pdf') ? (
                <iframe
                  src={documentUrl}
                  className="w-full h-[600px] border rounded"
                  title="ID Document"
                />
              ) : (
                <img
                  src={documentUrl}
                  alt="ID Document"
                  className="w-full h-auto rounded border"
                />
              )}
            </div>
          )}
        </DialogContent>
      </Dialog>

      {/* Rejection Dialog */}
      <Dialog open={showRejectDialog} onOpenChange={setShowRejectDialog}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Reject KYC Application</DialogTitle>
            <DialogDescription>
              Please provide a reason for rejecting this application. This will be logged in the audit trail.
            </DialogDescription>
          </DialogHeader>
          
          <div className="space-y-4">
            <div>
              <Label htmlFor="rejection-reason">Rejection Reason *</Label>
              <Textarea
                id="rejection-reason"
                placeholder="e.g., Document not clear, information mismatch, underage..."
                value={rejectionReason}
                onChange={(e) => setRejectionReason(e.target.value)}
                rows={4}
                className="mt-2"
              />
            </div>

            <div className="flex gap-2 justify-end">
              <Button
                variant="outline"
                onClick={() => {
                  setShowRejectDialog(false);
                  setRejectionReason("");
                }}
              >
                Cancel
              </Button>
              <Button
                variant="destructive"
                onClick={handleReject}
                disabled={actionLoading || !rejectionReason.trim()}
              >
                {actionLoading ? "Rejecting..." : "Confirm Rejection"}
              </Button>
            </div>
          </div>
        </DialogContent>
      </Dialog>
    </div>
  );
}
