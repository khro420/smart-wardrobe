import Layout from "@/components/Layout";
import CompletedChatView from "@/components/CompletedChatView";
export default async function ChatPage({ params }: { params: Promise<{ chat_id: string }> }) {
  const { chat_id } = await params;
  return <Layout><CompletedChatView key={chat_id} chatId={chat_id} /></Layout>;
}
