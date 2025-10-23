'use client';
import * as React from 'react';

export default function Page() {
  const [n, setN] = React.useState(0);
  return (
    <main style={{ padding: 24, fontFamily: 'system-ui' }}>
      <button
        onClick={() => setN(n + 1)}
        style={{ padding: '10px 16px', border: '1px solid #ccc', borderRadius: 8 }}
      >
        Clic : {n}
      </button>

      <div style={{ marginTop: 12 }}>
        <input type="file" />
      </div>
    </main>
  );
}
