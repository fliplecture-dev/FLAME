import { sessionValue } from "@/lib/api/auth-bff";
import { ProductHome } from "@/features/discovery/product-home";
export default async function Home() {
  return <ProductHome signedIn={Boolean(await sessionValue())} />;
}
