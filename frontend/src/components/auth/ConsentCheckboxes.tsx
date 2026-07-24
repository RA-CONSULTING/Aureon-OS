import { Checkbox } from "@/components/ui/checkbox";
import { Label } from "@/components/ui/label";
import { Link } from "react-router-dom";

interface ConsentCheckboxesProps {
  termsAccepted: boolean;
  privacyAccepted: boolean;
  riskAccepted: boolean;
  onTermsChange: (checked: boolean) => void;
  onPrivacyChange: (checked: boolean) => void;
  onRiskChange: (checked: boolean) => void;
}

export function ConsentCheckboxes({
  termsAccepted,
  privacyAccepted,
  riskAccepted,
  onTermsChange,
  onPrivacyChange,
  onRiskChange
}: ConsentCheckboxesProps) {
  return (
    <div className="space-y-3 pt-3 border-t border-border/30">
      <p className="text-xs font-medium text-muted-foreground">Legal Agreements</p>
      
      {/* Terms of Service */}
      <div className="flex items-start gap-2">
        <Checkbox
          id="terms"
          checked={termsAccepted}
          onCheckedChange={(checked) => onTermsChange(checked === true)}
          className="mt-0.5"
        />
        <Label htmlFor="terms" className="text-xs text-muted-foreground leading-tight cursor-pointer">
          I agree to the{" "}
          <Link to="/legal#terms" className="text-primary hover:underline" target="_blank">
            Terms of Service
          </Link>
          {" "}and understand that AUREON is an autonomous trading system.
        </Label>
      </div>

      {/* Privacy Policy */}
      <div className="flex items-start gap-2">
        <Checkbox
          id="privacy"
          checked={privacyAccepted}
          onCheckedChange={(checked) => onPrivacyChange(checked === true)}
          className="mt-0.5"
        />
        <Label htmlFor="privacy" className="text-xs text-muted-foreground leading-tight cursor-pointer">
          I agree to the{" "}
          <Link to="/legal#privacy" className="text-primary hover:underline" target="_blank">
            Privacy Policy
          </Link>
          {" "}and consent to encrypted storage of my API credentials.
        </Label>
      </div>

      {/* Trading Risk Acknowledgment */}
      <div className="flex items-start gap-2">
        <Checkbox
          id="risk"
          checked={riskAccepted}
          onCheckedChange={(checked) => onRiskChange(checked === true)}
          className="mt-0.5"
        />
        <Label htmlFor="risk" className="text-xs text-muted-foreground leading-tight cursor-pointer">
          I understand that{" "}
          <span className="text-warning font-medium">trading involves significant risk</span>
          {" "}and I may lose some or all of my investment. I am trading with funds I can afford to lose.
        </Label>
      </div>
    </div>
  );
}
