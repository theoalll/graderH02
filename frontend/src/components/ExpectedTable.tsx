import { ExpectedSubnet } from "../types";

export function ExpectedTable({ subnets }: { subnets: ExpectedSubnet[] }) {
  return (
    <div className="table-scroll">
      <table className="table">
        <thead>
          <tr>
            <th>Subnet</th>
            <th className="mono">Network</th>
            <th className="mono">Broadcast</th>
            <th className="mono">Mask</th>
            <th>/</th>
            <th>Max End Devices</th>
            <th>Max Hosts</th>
            <th className="mono">Host First</th>
            <th className="mono">Host Last</th>
            <th className="mono">Gateway</th>
          </tr>
        </thead>
        <tbody>
          {subnets.map((s) => (
            <tr key={s.name}>
              <td className="mono">{s.name}</td>
              <td className="mono">{s.network_address}</td>
              <td className="mono">{s.broadcast_address}</td>
              <td className="mono">{s.subnet_mask}</td>
              <td className="mono">{s.prefix}</td>
              <td>{s.max_hosts - 1}</td>
              <td>{s.max_hosts}</td>
              <td className="mono">{s.host_first}</td>
              <td className="mono">{s.host_last}</td>
              <td className="mono">{s.gateway}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
