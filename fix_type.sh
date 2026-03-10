#!/bin/bash
sed -i 's/(event: Event | MessageEvent | CloseEvent) => void/(event: Event) => void/g' app/src/hooks/useTradingEngine.test.tsx
sed -i 's/this.onopen({})/this.onopen(new Event("open"))/g' app/src/hooks/useTradingEngine.test.tsx
sed -i 's/this.onmessage({ data: JSON.stringify(data) } as MessageEvent)/this.onmessage(new MessageEvent("message", { data: JSON.stringify(data) }))/g' app/src/hooks/useTradingEngine.test.tsx
sed -i 's/this.onerror(error)/this.onerror(new Event("error"))/g' app/src/hooks/useTradingEngine.test.tsx
sed -i 's/this.onclose({} as CloseEvent)/this.onclose(new CloseEvent("close"))/g' app/src/hooks/useTradingEngine.test.tsx
sed -i 's/MockSocket.OPEN = 1;//g' app/src/hooks/useTradingEngine.test.tsx
sed -i 's/import { vi/import { vi, Mock/g' app/src/hooks/useTradingEngine.test.tsx
sed -i 's/vitest.Mock/Mock/g' app/src/hooks/useTradingEngine.test.tsx
