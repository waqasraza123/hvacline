import { OperationsLink, navigateOperations } from "./operations-link";
import { operationsHref } from "./dashboard-navigation";
import { ProductIcon } from "@/components/product-icons";
import { ContentPanel, EmptyState, MetricCard } from "@/components/ui/workspace-ui";
import type { ComponentProps, ReactNode } from "react";
import type { Operations, ScheduleResponse } from "./api";
import type { OperationsSection } from "./dashboard-shell";
import { DashboardTable, StatusBadge } from "./dashboard-table";
import styles from "./dashboard.module.css";

export function DashboardOverview({
  data,
  schedule,
  loadedAt,
  timestamp,
  children,
}: {
  data: Operations;
  schedule: ScheduleResponse | null;
  loadedAt: number;
  timestamp: (value: string) => string;
  children?: ReactNode;
}) {
  const upcoming = data.appointments
    .filter(
      (row) =>
        row.status === "CONFIRMED" && Date.parse(row.starts_at) >= loadedAt,
    )
    .sort((a, b) => Date.parse(a.starts_at) - Date.parse(b.starts_at));
  const handoffs = data.handoffs.filter((row) =>
    ["REQUESTED", "ACKNOWLEDGED"].includes(row.status),
  );
  const urgent = data.service_requests.filter(
    (row) =>
      row.service.hazardous_condition && row.status === "HANDOFF_REQUESTED",
  );
  const metrics: {
    label: string;
    value: number;
    icon: ComponentProps<typeof ProductIcon>["name"];
    section: OperationsSection;
    help: string;
  }[] = [
    {
      label: "Total calls",
      value: data.calls.length,
      icon: "phone",
      section: "calls",
      help: "Received calls in the loaded queue",
    },
    {
      label: "Service requests",
      value: data.service_requests.length,
      icon: "chat",
      section: "requests",
      help: "Confirmed customer details",
    },
    {
      label: "Confirmed bookings",
      value: data.appointments.filter((row) => row.status === "CONFIRMED").length,
      icon: "calendar",
      section: "bookings",
      help: "Confirmed in the loaded queue",
    },
    {
      label: "Pending follow-up",
      value: handoffs.length,
      icon: "clock",
      section: "handoffs",
      help: "Open callbacks and transfers",
    },
  ];

  return (
    <div className={styles.overview}>
      <section className={styles.metrics} aria-label="Loaded queue counts">
        {metrics.map((metric) => (
          <MetricCard
            key={metric.label}
            label={metric.label}
            value={metric.value}
            help={metric.help}
            icon={<ProductIcon name={metric.icon} />}
            href={operationsHref(metric.section)}
            onClick={() => navigateOperations(metric.section)}
          />
        ))}
      </section>
      <div className={styles.overviewGrid}>
        <section className={styles.panel} aria-labelledby="upcoming-heading">
          <div className={styles.panelHeading}>
            <div>
              <h2 id="upcoming-heading">Upcoming appointments</h2>
              <p>Next confirmed visits in the loaded queue.</p>
            </div>
            <OperationsLink className={styles.dashboardAction} section="bookings">
              View all
            </OperationsLink>
          </div>
          {upcoming.length === 0 ? (
            <div className={styles.emptyState}>
              <ProductIcon name="calendar" />
              <h3>No upcoming visits in this queue</h3>
              <p>
                Confirmed appointments will appear here. Review requests to book
                the next visit.
              </p>
              <OperationsLink className={styles.dashboardAction} section="requests">
                View service requests
              </OperationsLink>
            </div>
          ) : (
            <DashboardTable
              caption="Next confirmed appointments"
              headings={["Customer", "Appointment", "Team", "Status"]}
            >
              {upcoming.slice(0, 5).map((appointment) => {
                const request = data.service_requests.find(
                  (row) => row.id === appointment.service_request_id,
                );
                const team = schedule?.configuration?.teams.find(
                  (row) => row.key === appointment.team_key,
                );
                return (
                  <tr key={appointment.id}>
                    <td>
                      <strong>
                        {request?.customer.full_name ?? "Service request"}
                      </strong>
                      <span className={styles.cellHelp}>
                        {request?.service.kind.replaceAll("_", " ") ??
                          "Details in appointments"}
                      </span>
                    </td>
                    <td>{timestamp(appointment.starts_at)}</td>
                    <td>{team?.name ?? appointment.team_key}</td>
                    <td>
                      <StatusBadge status={appointment.status} />
                    </td>
                  </tr>
                );
              })}
            </DashboardTable>
          )}
        </section>
        <section className={styles.panel} aria-labelledby="attention-heading">
          <div className={styles.panelHeading}>
            <div>
              <h2 id="attention-heading">Needs attention</h2>
              <p>Follow-up for your team.</p>
            </div>
            <span className={styles.attentionCount}>
              {handoffs.length + urgent.length}
            </span>
          </div>
          {handoffs.length === 0 && urgent.length === 0 ? (
            <div className={styles.emptyState}>
              <ProductIcon name="check" />
              <h3>No pending follow-up in this queue</h3>
              <p>
                New callbacks, transfers and urgent requests will appear here.
              </p>
            </div>
          ) : (
            <ul className={styles.attentionList}>
              {urgent.slice(0, 2).map((request) => (
                <li key={request.id}>
                  <span className={styles.urgentIcon}>
                    <ProductIcon name="shield" />
                  </span>
                  <div>
                    <strong>Urgent service request</strong>
                    <p>{request.customer.full_name}</p>
                    <span className={styles.cellHelp}>
                      Human attention required
                    </span>
                  </div>
                  <OperationsLink className={styles.dashboardAction} section="requests">
                    Review
                    <span className={styles.srOnly}>
                      {" "}
                      urgent service requests
                    </span>
                  </OperationsLink>
                </li>
              ))}
              {handoffs.slice(0, 4).map((handoff) => (
                <li key={handoff.id}>
                  <span className={styles.metricIcon}>
                    <ProductIcon
                      name={handoff.kind === "CALLBACK" ? "phone" : "chat"}
                    />
                  </span>
                  <div>
                    <strong>
                      {handoff.kind === "CALLBACK"
                        ? "Callback requested"
                        : "Human transfer"}
                    </strong>
                    <p>{handoff.reason}</p>
                    <StatusBadge status={handoff.status} />
                  </div>
                  <OperationsLink className={styles.dashboardAction} section="handoffs">
                    Review<span className={styles.srOnly}> follow-up</span>
                  </OperationsLink>
                </li>
              ))}
            </ul>
          )}
          {(urgent.length > 0 || handoffs.length > 0) && (
            <div className={styles.panelFooter}>
              {urgent.length > 0 && (
                <OperationsLink className={styles.dashboardAction} section="requests">
                  All service requests
                </OperationsLink>
              )}
              {handoffs.length > 0 && (
                <OperationsLink className={styles.dashboardAction} section="handoffs">
                  All follow-up
                </OperationsLink>
              )}
            </div>
          )}
        </section>
      </div>
      <ContentPanel title="Recent conversations" description="Latest received calls in the loaded queue. Browser conversation history is not included."
        actions={<OperationsLink className={styles.dashboardAction} section="calls">View calls</OperationsLink>}>
        {data.calls.length === 0 ? <EmptyState title="No calls in this queue">Received calls will appear here after the workspace refreshes.</EmptyState> :
          <DashboardTable caption="Recent received calls" headings={["Caller", "Received", "Status"]}>
            {[...data.calls].sort((a, b) => Date.parse(b.received_at) - Date.parse(a.received_at)).slice(0, 5).map((call) => <tr key={call.id}>
              <td>{call.caller_number ?? "Caller number unavailable"}</td><td>{timestamp(call.received_at)}</td><td><StatusBadge status={call.status} /></td>
            </tr>)}
          </DashboardTable>}
      </ContentPanel>
      {children && <div className={styles.featureGrid}>{children}</div>}
      <section className={styles.nextStep}>
        <span className={styles.metricIcon}>
          <ProductIcon name="calendar" />
        </span>
        <div>
          <h2>Keep your availability up to date</h2>
          <p>
            Review service areas, opening hours and team calendars before
            accepting new bookings.
          </p>
        </div>
        <OperationsLink className={styles.dashboardAction} section="scheduling">
          Manage scheduling
          <ProductIcon name="arrow" />
        </OperationsLink>
      </section>
    </div>
  );
}
