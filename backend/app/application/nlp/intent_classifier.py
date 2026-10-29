"""Bounded request patterns, not clothing-keyword classification."""
import re


class IntentClassifier:
    def classify(self, text: str) -> bool:
        if re.search(r"\b(buy|purchase|shop online|delete|remove|archive|sell|explain|define|manufactur\w*|write|translate|ignore|instructions|password|weather forecast)\b", text):
            return False
        return bool(re.search(
            r"\b(?:suggest|recommend|give me|show me|help me (?:choose|pick))\b.*\b(?:outfit|clothes|clothing|look|something)\b"
            r"|\bwhat (?:should|can) i wear\b", text))
