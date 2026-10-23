/**
 * Local console — the page that used to be a separate listener on port 8080.
 *
 * Dashboard and Command Center are tabs of this shell. The launcher does not
 * bind 8080. Live trading stays off. No order is placed from this page.
 */

import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";

const CIRCULATION = "http://127.0.0.1:8799/health";
const GATEWAY = "http://127.0.0.1:8790/healthz";
const FUSION = "http://127.0.0.1:8765/healthz";
const STATUS = "http://127.0.0.1:8791/healthz";
const ORCA = "http://127.0.0.1:8888/health";

export default function LauncherPage() {
  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center gap-2">
        <Badge>DRY RUN · LIVE TRADING OFF · PAPER DEFAULT</Badge>
        <Badge variant="outline">port 8080 is not bound by the launcher</Badge>
      </div>
      <div>
        <h1 className="text-2xl font-medium tracking-tight">Aureon OS — local console</h1>
        <p className="text-sm text-muted-foreground">
          This tab is the self-hosted console. The product shell stays on this
          dev server. Status calls do not place orders.
        </p>
      </div>
      <Tabs defaultValue="dashboard">
        <TabsList>
          <TabsTrigger value="dashboard">Dashboard</TabsTrigger>
          <TabsTrigger value="command-center">Command Center</TabsTrigger>
        </TabsList>
        <TabsContent value="dashboard" className="space-y-3">
          <Card>
            <CardHeader>
              <CardTitle>Dashboard</CardTitle>
              <CardDescription>Thought bus, fusion seat, and market status. Live trading stays off.</CardDescription>
            </CardHeader>
            <CardContent className="space-y-2 text-sm">
              <p>
                Thought bus: <a className="text-primary underline" href={CIRCULATION}>{CIRCULATION}</a>
              </p>
              <p>
                Fusion seat: <a className="text-primary underline" href={FUSION}>{FUSION}</a>
              </p>
              <p>
                Market status: <a className="text-primary underline" href={STATUS}>{STATUS}</a>
              </p>
              <p className="text-muted-foreground">
                Circulation listens on 8799. The fusion seat keeps 8765 and answers other paths with its own token.
              </p>
            </CardContent>
          </Card>
        </TabsContent>
        <TabsContent value="command-center" className="space-y-3">
          <Card>
            <CardHeader>
              <CardTitle>Command Center</CardTitle>
              <CardDescription>Operator gateway and Orca. Both stay on loopback. No order is placed.</CardDescription>
            </CardHeader>
            <CardContent className="space-y-2 text-sm">
              <p>
                Operator gateway: <a className="text-primary underline" href={GATEWAY}>{GATEWAY}</a>
              </p>
              <p>
                Orca: <a className="text-primary underline" href={ORCA}>{ORCA}</a>
              </p>
              <p className="text-muted-foreground">
                The overview shows gateway offline until 8790/healthz answers. This tab does not open a second dashboard on 8080.
              </p>
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  );
}
