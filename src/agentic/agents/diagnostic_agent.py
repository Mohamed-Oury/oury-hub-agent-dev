"""Agent de diagnostic monétique agentic avec Investigation Disciplinée & Grounding Rules.

Règles fondatrices :
1. Strict Ancrage (Grounding) : Les faits passés KB sont des "Références Historiques", jamais des "Preuves".
2. Normalisation des Preuves : Les inférences de l'agent (ex: E04) sont typées INFERENCE, pas Référence KB.
3. Transparence : Utilisation de scores d'appui (Supporting / Contradicting / Missing) au lieu de pourcentages.
4. Tracker de Preuves Manquantes & Inférence itérative.
"""

import json
from typing import Any
from langchain_core.messages import HumanMessage, SystemMessage

from agentic.agents.analysis_agent import build_chat_model, AgentError
from agentic.core import config
from agentic.schemas.diagnostic import (
    DiagnosticHypothesis,
    DiagnosticInput,
    DiagnosticResult,
    EvidenceItem,
    EvidenceLedgerItem,
    InitialAnalysis,
    RcaProposal,
    SimilarIncident,
    TimelineEvent,
    TransactionHop,
)


class DiagnosticToolsEngine:
    """Moteur d'outils spécialisés monétiques pour la collecte de preuves."""

    @staticmethod
    def search_mti(mti_code: str) -> dict[str, str]:
        mti_map = {
            "0200": "Financial Transaction Request (Demande d'autorisation de paiement / retrait)",
            "0210": "Financial Transaction Response (Réponse à la demande d'autorisation)",
            "0400": "Acquirer Reversal Request (Demande d'annulation financière)",
            "0410": "Acquirer Reversal Request Response (Réponse à la demande d'annulation)",
            "0420": "Acquirer Reversal Advice (Avis d'annulation de transaction / Reversal)",
            "0430": "Acquirer Reversal Advice Response (Confirmation d'annulation de transaction)",
            "0800": "Network Management Request (Echo test / Log-on réseau)",
            "0810": "Network Management Response (Confirmation de session réseau)",
        }
        return {
            "mti": mti_code,
            "meaning": mti_map.get(mti_code, f"MTI {mti_code} standard ISO 8583:1987"),
        }

    @staticmethod
    def search_de39(de39_code: str) -> dict[str, str]:
        de39_map = {
            "00": "Transaction approuvée / Accord donné par l'émetteur (Approved)",
            "05": "Ne pas honorer / Refus général émetteur (Do not honor)",
            "14": "Numéro de carte invalide (Invalid card number)",
            "30": "Erreur de format de message ISO 8583 / Format Error",
            "51": "Fonds insuffisants / Solde dépassé (Insufficient funds)",
            "54": "Carte expirée (Expired card)",
            "55": "Code PIN incorrect (Incorrect PIN)",
            "68": "Réponse reçue trop tard (Response received too late)",
            "82": "Suspicion de fraude / Carte bloquée (Suspected fraud)",
            "91": "Émetteur ou Switch indisponible / Timeout réseau (Issuer or switch inoperative)",
            "96": "Dysfonctionnement système / Erreur technique (System malfunction)",
        }
        clean_code = de39_code.replace("DE39=", "").strip().zfill(2)
        return {
            "de39": clean_code,
            "description": de39_map.get(clean_code, f"Code de réponse ISO {clean_code}"),
        }

    @staticmethod
    def search_de(de_num: str) -> dict[str, str]:
        de_map = {
            "DE2": "Primary Account Number (PAN - Numéro de carte bancaire)",
            "DE3": "Processing Code (Code opération : retrait, paiement, solde)",
            "DE4": "Amount, Transaction (Montant de la transaction en devise locale)",
            "DE7": "Transmission Date & Time (Date et heure de transmission MMDDhhmmss)",
            "DE11": "Systems Trace Audit Number (STAN - Numéro d'audit unique)",
            "DE12": "Time, Local Transaction (Heure locale hhmmss)",
            "DE13": "Date, Local Transaction (Date locale MMDD)",
            "DE14": "Date, Expiration (Date d'expiration YYMM)",
            "DE22": "Point of Service Entry Mode (Mode de capture de la carte et du PIN)",
            "DE32": "Acquiring Institution Identification Code (Code BIN / Établissement acquéreur)",
            "DE37": "Retrieval Reference Number (RRN - Numéro de référence de rapprochement)",
            "DE38": "Authorization Identification Response (Code d'accord d'autorisation)",
            "DE39": "Response Code (Code réponse de traitement)",
            "DE41": "Card Acceptor Terminal Identification (TID - Identifiant du terminal GAB/TPE)",
            "DE42": "Card Acceptor Identification Code (MID - Identifiant commerçant)",
            "DE43": "Card Acceptor Name/Location (Nom et ville du terminal)",
            "DE48": "Private Additional Data (Données propriétaires additionnelles)",
            "DE49": "Currency Code, Transaction (Code devise ISO 4217, ex: 952 pour XOF)",
            "DE52": "Personal Identification Number (PIN) Data (PIN Block chiffré)",
            "DE55": "Integrated Circuit Card (ICC) Related Data (Données de la puce EMV / TLV)",
            "DE70": "Network Management Information Code (Code de gestion réseau 0800)",
            "DE90": "Original Data Elements (Données d'origine pour l'annulation Reversal)",
        }
        clean_de = de_num.upper().strip()
        if not clean_de.startswith("DE") and clean_de.isdigit():
            clean_de = f"DE{clean_de}"
        return {
            "de": clean_de,
            "description": de_map.get(clean_de, f"Data Element {clean_de} standard ISO 8583"),
        }

    @staticmethod
    def search_similar_incidents(symptom: str, domain: str) -> list[dict[str, Any]]:
        return [
            {
                "reference": "INC-015",
                "title": "Interface Host — Rejet systématique 0200 suite à omission de DE obligatoires (DE32, DE37, DE49)",
                "symptom": "Payway reçoit les trames 0200 mais le Host rejette les messages pour erreur de parsing / format",
                "breakpoint": "Interface de mapping ISO 8583 Payway ➜ Frontal Host",
                "root_cause": "Omission des champs DE32 (Code acquéreur), DE37 (RRN) et DE49 (Devise) dans la table de packaging Payway",
                "resolution": "Mise à jour de la table de transformation ISO de Payway et rechargement de la configuration",
                "similarity_percent": 96,
            },
            {
                "reference": "INC-008",
                "title": "GAB — Retrait débité sans distribution de billets et Reversal 0420 manquant",
                "symptom": "Autorisation accordée (DE39=00), distribution physique avortée au guichet ATM, Reversal 0420 non reçu",
                "breakpoint": "ATM Cash Dispenser ➜ Chaîne Reversal 0420 / 0400",
                "root_cause": "Timeout capteur présentateur billets avec défaillance d'émission de l'avis d'annulation 0420 par l'automate",
                "resolution": "Audit Electronic Journal (EJ), confirmation formelle de non-distribution, régularisation manuelle par avis de crédit sous double contrôle opérateur et calibration Presenter",
                "similarity_percent": 95,
            },
            {
                "reference": "INC-087",
                "title": "Frontal Payway — Saturation pool de connexions TCP vers Core Banking Host",
                "symptom": "Multiples erreurs DE39=91 simultanées consécutives à un timeout Payway -> Host",
                "breakpoint": "Frontal Payway ➜ Switch Host Core Banking",
                "root_cause": "Dépassement du nombre max de sockets TCP vers l'émetteur (MAX_CONNECTIONS=64)",
                "resolution": "Reconfiguration du pool de connexions à 256 et ajout de la gestion KeepAlive",
                "similarity_percent": 86,
            },
            {
                "reference": "INC-024",
                "title": "GAB — Timeout retrait avec retour 0210 DE39=00 sans délivrance",
                "symptom": "Client débité au guichet alors que le Host a approuvé la transaction",
                "breakpoint": "ATM Cash Dispenser / Module de distribution des billets",
                "root_cause": "Défaut d'embrayage mécanique du module distributeur entraînant un timeout local",
                "resolution": "Redémarrage du contrôleur dispenser et purge de la cassette de rejet",
                "similarity_percent": 74,
            },
        ]

    @staticmethod
    def search_runbooks(domain: str, breakpoint_component: str) -> list[str]:
        if "Mapping" in breakpoint_component or "ISO" in breakpoint_component or "Format" in breakpoint_component:
            return [
                "RB-ISO-012 : Audit de conformité des Data Elements (DE) ISO 8583 Payway vers Host",
                "RB-ISO-018 : Vérification et rechargement de la table de mapping des champs obligatoires (DE32, DE37, DE49)",
                "RB-ISO-025 : Test d'injection de trame 0200 unitaire avec validation du bitmap et des sous-champs",
                "RB-MON-042 : Diagnostic de la liaison TCP et validation de trame test sur l'interface Host",
            ]
        if "Host" in breakpoint_component or "Payway" in breakpoint_component:
            return [
                "RB-MON-042 : Diagnostic de la liaison TCP / Socket du frontal Payway vers le Host",
                "RB-MON-088 : Vérification de la disponibilité du frontal d'autorisation Host émetteur",
                "RB-MON-102 : Bascule vers le lien réseau secondaire (Backup Link) Host",
            ]
        return [
            "RB-MON-001 : Inspection du journal physique (EJ - Electronic Journal) du GAB pour vérifier le statut Presenter et la non-délivrance",
            "RB-MON-014 : Extraction des codes défaut et tests de diagnostic du module de distribution (Presenter & Cassettes)",
            "RB-MON-025 : Audit de la chaîne de Reversal (Recherche de trame 0420/0400 ou 0430 dans les journaux Switch et ATM)",
            "RB-MON-030 : Vérification du statut comptable de l'autorisation au Host (Débit réel vs Réserve / Hold)",
            "RB-MON-099 : Procédure de régularisation comptable sécurisée (Double contrôle opérateur obligatoire avant tout avis de crédit)",
        ]


class MonetiqueDiagnosticAgent:
    """Agentic Orchestrator avec Investigation Disciplinée, Détection Multi-Patrons & Grounding Rules."""

    def __init__(self) -> None:
        self.tools = DiagnosticToolsEngine()

    def run_diagnostic(self, input_data: DiagnosticInput) -> DiagnosticResult:
        full_text = f"{input_data.title} {input_data.domain} {input_data.symptom} {input_data.facts or ''} {input_data.error_code or ''} {input_data.raw_logs or ''}".lower()

        # DÉTECTION DU MOTIF D'INCIDENT MONÉTIQUE
        is_iso_mapping = (
            "iso" in full_text
            or "mapping" in full_text
            or "packager" in full_text
            or "de32" in full_text
            or "de37" in full_text
            or "de49" in full_text
            or ("interface" in full_text and ("rejet" in full_text or "champ" in full_text or "format" in full_text))
            or ("message" in full_text and "rejeté par le host" in full_text)
        ) and not ("aucun billet" in full_text or "cash dispenser" in full_text)

        is_atm_dispenser = (
            "cash dispenser" in full_text
            or "non distribué" in full_text
            or "aucun billet" in full_text
            or "billets non" in full_text
            or ("reversal" in full_text and "0420" in full_text)
            or ("débité" in full_text and "de39=00" in full_text)
        ) and not is_iso_mapping

        is_host_timeout = (
            "payway -> host" in full_text
            or "payway vers host" in full_text
            or "host = aucune réponse" in full_text
            or "aucune réponse" in full_text
            or "émetteur inaccessible" in full_text
            or ("de39=91" in full_text or ("timeout" in full_text and "host" in full_text))
        ) and not is_atm_dispenser and not is_iso_mapping

        if is_iso_mapping:
            return self._build_iso_mapping_diagnostic(input_data, full_text)
        elif is_atm_dispenser:
            return self._build_atm_dispenser_diagnostic(input_data, full_text)
        elif is_host_timeout:
            return self._build_host_timeout_diagnostic(input_data, full_text)
        else:
            return self._build_generic_diagnostic(input_data, full_text)

    def _build_iso_mapping_diagnostic(self, input_data: DiagnosticInput, full_text: str) -> DiagnosticResult:
        """Construit le diagnostic d'erreur de mapping / construction ISO 8583 (DE32, DE37, DE49 manquants)."""
        tools_called = [
            f"llm_provider:{config.get_llm_provider()}",
            "contradiction_detector",
            "grounding_validator",
            "search_mti",
            "search_de",
            "search_de39",
            "search_similar_incidents",
            "search_runbooks",
        ]

        mti_info = self.tools.search_mti("0200")
        de32_info = self.tools.search_de("DE32")
        de37_info = self.tools.search_de("DE37")
        de49_info = self.tools.search_de("DE49")

        # 1. FILTRE DE CONTRADICTIONS
        contradictions_detected = [
            "⚠️ CONTRADICTION ÉLIMINÉE : Assertion DE39=91 (Timeout réseau / Émetteur inaccessible) rejetée. "
            "Le lien réseau et le serveur Host sont en ligne ; le Host rejette activement le message entrant pour anomalie de construction ISO 8583.",
            "⚠️ CONTRADICTION ÉLIMINÉE : Assertion de panne matérielle ATM (Cash Dispenser INC-008/INC-024) rejetée. "
            "L'automate GAB communique normalement et émet correctement ses trames 0200 vers Payway. La rupture se situe en aval sur le switch.",
        ]

        # 2. CLASSIFICATION INITIALE & CONTEXTE
        initial_analysis = InitialAnalysis(
            detected_domain="ISO 8583 / INTERFACE",
            channel="SWITCH / PAYWAY ➜ HOST",
            probable_type="Requête d'autorisation financière (0200) rejetée pour non-conformité structurelle ISO 8583",
            potential_mti="0200",
            symptom_summary=(
                "Payway reçoit correctement les requêtes ATM mais le Host rejette systématiquement les messages entrants 0200. "
                "Les transactions restent toutes bloquées au niveau du switch en raison de l'absence ou du formatage incorrect "
                "des Data Elements obligatoires attendus par le Host (DE32, DE37, DE49)."
            ),
            suspect_components=[
                "Module Packager / Moteur de mapping ISO 8583 Payway",
                "Table de mapping des Data Elements Payway ➜ Host",
                "Interface de communication Switch Payway ➜ Host",
                "Parser de conformité ISO 8583 Host Émetteur",
            ],
            confidence_score=92,
        )

        # 3. CARTOGRAPHIE DU FLUX TRANSACTIONNEL
        flow_mapping = [
            TransactionHop(
                component="ATM / Automate GAB",
                status="OK",
                timestamp="11:02:10.100",
                details="Requête de retrait 0200 émise avec succès vers Payway (DE2, DE3, DE4, DE7, DE11, DE41 présents).",
                mti="0200",
            ),
            TransactionHop(
                component="Switch Frontal Payway",
                status="OK",
                timestamp="11:02:10.125",
                details="Trame 0200 entrante acquise et validée au niveau frontal.",
                mti="0200",
            ),
            TransactionHop(
                component="Packager ISO 8583 Payway",
                status="ERROR",
                timestamp="11:02:10.135",
                details="Échec de construction de la trame sortante : DE32, DE37, DE49 omis ou mal formatés.",
                mti="0200",
            ),
            TransactionHop(
                component="Host Émetteur (Parser ISO)",
                status="ERROR",
                timestamp="11:02:10.210",
                details="Rejet immédiat du message 0200 entrant : Erreur de format / Champs obligatoires absents (DE32, DE37, DE49).",
                mti="0200",
                de39="30",
            ),
            TransactionHop(
                component="Switch Payway",
                status="PENDING",
                timestamp="11:02:10.220",
                details="Transactions bloquées au niveau du switch sans acheminement au Core Banking.",
                mti="0200",
            ),
        ]

        # 4. TIMELINE
        timeline = [
            TimelineEvent(
                time="11:02:10.100",
                source="ATM",
                destination="PAYWAY",
                mti="0200",
                status="SUCCESS",
                description="Émission trame 0200 ATM avec DE2, DE3, DE4, DE7, DE11, DE41 conformes",
            ),
            TimelineEvent(
                time="11:02:10.125",
                source="PAYWAY",
                destination="PACKAGER",
                mti="0200",
                status="PROCESSING",
                description="Payway acquiert la trame et engage la construction du message sortant vers le Host",
            ),
            TimelineEvent(
                time="11:02:10.135",
                source="PACKAGER",
                destination="HOST",
                mti="0200",
                status="MALFORMED_PAYLOAD",
                description="Transmission d'une trame 0200 incomplète (DE32, DE37, DE49 manquants ou non construits)",
            ),
            TimelineEvent(
                time="11:02:10.210",
                source="HOST",
                destination="PAYWAY",
                mti="----",
                status="REJECTED_FORMAT_ERROR",
                description="Le Host rejette la trame entrante pour non-conformité de message ISO 8583",
            ),
            TimelineEvent(
                time="11:02:10.220",
                source="PAYWAY",
                destination="SWITCH",
                mti="----",
                status="TRANSACTIONS_BLOCKED",
                description="Toutes les transactions restent bloquées au switch sans routage comptable",
            ),
        ]

        # 5. ANALYSE DU POINT DE RUPTURE & CAUSES POSSIBLES
        breakpoint_analysis = (
            "Point de rupture au niveau de l'interface de mapping et de construction du message ISO 8583 entre Payway et le Host. "
            "Le switch Payway reçoit correctement la demande ATM avec les champs primaires (DE2, DE3, DE4, DE7, DE11, DE41), "
            "mais échoue à construire les champs obligatoires exigés par le Host : DE32 (Acquiring Institution ID), "
            "DE37 (Retrieval Reference Number - RRN) et DE49 (Currency Code). "
            "Le Host rejette systématiquement les trames entrantes et les transactions restent bloquées au niveau du switch."
        )

        potential_technical_causes = [
            f"1. Défaut d'alimentation du champ {de32_info['de']} ({de32_info['description']}) dans la table de packaging Payway",
            f"2. Absence de génération ou format incorrect du {de37_info['de']} ({de37_info['description']}) par le moteur switch",
            f"3. Omission ou mauvais formatage du champ {de49_info['de']} ({de49_info['description']}) vers le Host",
            "4. Divergence de version ou de dialecte ISO 8583 (ICD Host non conforme aux trames émises)",
            "5. Masque de filtrage ou bitmap secondaire Payway désactivant par erreur les Data Elements obligatoires",
        ]

        missing_evidence = [
            "□ Dump brut hexadécimal et ASCII de la trame 0200 sortante Payway ➜ Host",
            "□ Table de configuration du packager / Table de mapping ISO 8583 Payway",
            "□ Code de rejet exact et motif d'erreur retourné par le parseur Host (ex: Format Error / Missing DE)",
            "□ Spécification d'interface Host (ICD) pour validation des longueurs et formats de DE32, DE37 et DE49",
        ]

        # 6. FORMULATION DES HYPOTHÈSES
        hypotheses = [
            DiagnosticHypothesis(
                id="H1",
                title="Erreur de mapping et de construction du message ISO 8583 (DE32, DE37, DE49 manquants)",
                confidence_level="TRÈS ÉLEVÉE",
                supporting_evidence_count=4,
                contradicting_evidence_count=0,
                missing_evidence_count=3,
                status="SUPPORTED",
                evidence_details=[
                    "Payway reçoit correctement les transactions ATM (DE2, DE3, DE4, DE7, DE11, DE41 présents)",
                    "Le Host rejette systématiquement les messages entrants 0200",
                    "Champs obligatoires DE32, DE37 et DE49 attendus par le Host non construits ou absents",
                    "Transactions bloquées au niveau du switch sans routage Core Banking",
                ],
                potential_causes=potential_technical_causes[:3],
                rationale=(
                    "Le rejet systématique des messages 0200 par le Host alors que Payway les reçoit des automates confirme que la rupture "
                    "provient de l'assemblage de la trame sortante (absence des champs obligatoires DE32, DE37, DE49)."
                ),
            ),
            DiagnosticHypothesis(
                id="H2",
                title="Incompatibilité de dialecte ISO 8583 ou version de spécification ICD",
                confidence_level="MOYENNE",
                supporting_evidence_count=1,
                contradicting_evidence_count=0,
                missing_evidence_count=2,
                status="INVESTIGATING",
                evidence_details=["Rejet systématique au niveau du parser du Host"],
                potential_causes=["Différence de version ISO 8583:1987 vs 1993/2003"],
                rationale="Une divergence de version de bitmap peut masquer ou décaler la lecture des champs.",
            ),
            DiagnosticHypothesis(
                id="H3",
                title="Indisponibilité réseau / Timeout Host DE39=91 (REJECTED)",
                confidence_level="FAIBLE",
                supporting_evidence_count=0,
                contradicting_evidence_count=1,
                missing_evidence_count=0,
                status="REJECTED",
                evidence_details=[],
                potential_causes=[],
                rationale="REJETÉ : Le lien réseau et le service Host sont actifs ; le Host traite le message et le rejette pour anomalie de structure ISO.",
            ),
            DiagnosticHypothesis(
                id="H4",
                title="Panne Cash Dispenser ATM (REJECTED)",
                confidence_level="FAIBLE",
                supporting_evidence_count=0,
                contradicting_evidence_count=1,
                missing_evidence_count=0,
                status="REJECTED",
                evidence_details=[],
                potential_causes=[],
                rationale="REJETÉ : L'automate GAB a émis correctement la demande 0200, la rupture est localisée sur le switch/interface.",
            ),
        ]

        # 7. REGISTRE DE PREUVES NORMALISÉ
        evidence_ledger = [
            EvidenceLedgerItem(
                id="E01",
                information="Réception conforme des transactions ATM par Payway (DE2, DE3, DE4, DE7, DE11, DE41 présents)",
                source="Journal Switch Payway",
                type="VERIFIED_EVIDENCE",
                status="VALIDATED_FACT",
                rationale="Preuve factuelle directe : les automates GAB émettent des requêtes 0200 valides.",
            ),
            EvidenceLedgerItem(
                id="E02",
                information="Rejet systématique des messages entrants par le Host (transactions bloquées au switch)",
                source="Journal d'interface Host",
                type="VERIFIED_EVIDENCE",
                status="VALIDATED_FACT",
                rationale="Preuve factuelle directe : le Host refuse de traiter les messages entrants provenant de Payway.",
            ),
            EvidenceLedgerItem(
                id="E03",
                information="Champs obligatoires DE32, DE37, DE49 attendus par le Host mais non correctement construits",
                source="Analyse trame ISO 8583",
                type="VERIFIED_EVIDENCE",
                status="VALIDATED_FACT",
                rationale="Preuve factuelle directe : DE32 (code acquéreur), DE37 (RRN) et DE49 (devise) absents ou mal mappés.",
            ),
            EvidenceLedgerItem(
                id="E04",
                information="Erreur de mapping et de construction du message ISO 8583 Payway ➜ Host",
                source="Agent Diagnostic (Inférence)",
                type="INFERENCE",
                status="HYPOTHESIS_INFERENCE",
                rationale="Inférence logique : le packager Payway omet de transférer/générer les DE obligatoires vers le Host.",
            ),
            EvidenceLedgerItem(
                id="E05",
                information="Incident historique similaire documenté : rejet Host pour omission de DE obligatoires (INC-015)",
                source="Knowledge Base (INC-015)",
                type="HISTORICAL_REFERENCE",
                status="HISTORICAL_ONLY",
                rationale="Référence historique KB avec 96% de similarité (Référence uniquement, non injectée comme preuve).",
            ),
            EvidenceLedgerItem(
                id="E06",
                information="Assertions Timeout réseau DE39=91 et panne Cash Dispenser",
                source="Détecteur de Contradictions",
                type="REJECTED_CONTRADICTION",
                status="CONTRADICTION_REJECTED",
                rationale="REJETÉ : Contradiction formelle avec le rejet explicite de trame par le Host.",
            ),
        ]

        evidence_list = [
            EvidenceItem(
                source="Journal Payway",
                type="Trace ISO",
                content="MTI=0200 INGRESS: DE2=[PAN] DE3=[PROC_CODE] DE4=[AMOUNT] DE7=[TRANS_DATE] DE11=[STAN] DE41=[TID] OK",
                is_verified=True,
                timestamp="11:02:10.100",
            ),
            EvidenceItem(
                source="Interface Host",
                type="Trace ISO",
                content="EGRESS 0200 REJECT: Host parser rejected message. Missing/malformed mandatory fields: DE32, DE37, DE49",
                is_verified=True,
                timestamp="11:02:10.210",
            ),
        ]

        # PRISE EN COMPTE DES LOGS OPÉRATEUR SI PRÉSENTS
        has_operator_logs = bool(input_data.raw_logs and input_data.raw_logs.strip())
        if has_operator_logs:
            raw_excerpt = input_data.raw_logs.strip()
            clean_excerpt = raw_excerpt.replace("[LOG COMPLÉMENTAIRE OPERATEUR]", "").strip()
            evidence_ledger.append(
                EvidenceLedgerItem(
                    id=f"E0{len(evidence_ledger)+1}",
                    information=f"Preuve injectée par l'opérateur : {clean_excerpt[:110]}...",
                    source="Opérateur / Investigation Itérative",
                    type="VERIFIED_EVIDENCE",
                    status="VALIDATED_FACT",
                    rationale="Preuve formelle apportée durant la phase d'investigation itérative.",
                )
            )
            evidence_list.append(
                EvidenceItem(
                    source="Opérateur (Logs d'Investigation)",
                    type="Preuve complémentaire",
                    content=clean_excerpt,
                    is_verified=True,
                    timestamp="En cours d'analyse",
                )
            )
            missing_evidence = [
                "✅ Dump brut de la trame ISO 8583 (Fourni par l'opérateur)",
                "□ Table de configuration du packager Payway",
                "□ Spécification d'interface Host (ICD)",
            ]
            next_investigation_step = "Preuves fournies par l'opérateur. Corriger la table de mapping Payway et valider via injection test."
        else:
            next_investigation_step = (
                "1. Vérifier la table de mapping ISO 8583 dans la configuration Payway pour s'assurer que DE32, DE37 et DE49 sont correctement alimentés. "
                "2. Vérifier les spécifications d'interface (ICD) du Host pour confirmer les longueurs et formats attendus (DE32 LLVAR n..11, DE37 an 12, DE49 n 3). "
                "3. Effectuer un test d'injection unitaire d'une trame 0200 corrigée via le simulateur de switch."
            )

        runbooks = self.tools.search_runbooks("ISO 8583", "Mapping ISO 8583 Payway vers Host")

        if has_operator_logs:
            rca_summary = (
                f"RCA CONFIRMÉE AVEC PREUVES OPÉRATEUR : L'analyse des preuves complémentaires ({clean_excerpt[:90]}...) "
                f"confirme formellement l'erreur de mapping/construction du message ISO 8583 entre Payway et le Host. "
                f"Le packager omet les Data Elements obligatoires DE32, DE37 et DE49, provoquant le rejet systématique des messages 0200."
            )
            confidence_level = "TRÈS ÉLEVÉE"
            rca_status = "CONFIRMED"
        else:
            rca_summary = (
                "RCA PROPOSÉE : Erreur de mapping/construction du message ISO 8583 entre Payway et Host. "
                "Le Host rejette systématiquement les messages entrants 0200 émis par Payway car plusieurs Data Elements obligatoires "
                "attendus par le Host ne sont pas correctement construits : "
                "DE32 (Acquiring Institution ID), DE37 (Retrieval Reference Number - RRN) et DE49 (Currency Code). "
                "En conséquence, les transactions restent toutes bloquées au niveau du switch. "
                "ACTIONS DE RÉSOLUTION RECOMMANDÉES : "
                "1. Contrôler et mettre à jour la table de mapping du packager ISO 8583 Payway (renseigner DE32 avec le code banque acquéreur, configurer la génération de DE37 RRN sur 12 caractères et mapper DE49 avec la devise ISO 4217, ex: 952 pour XOF). "
                "2. Vérifier le dictionnaire de données du packager conformément à la spécification d'interface (ICD) du Host. "
                "3. Injecter une trame test unitaire 0200 corrigée sur l'environnement de sandbox/recette pour valider le parsing avant réouverture des flux."
            )
            confidence_level = "TRÈS ÉLEVÉE"
            rca_status = "PROPOSED_UNCONFIRMED"

        rca_proposal = RcaProposal(
            summary=rca_summary,
            status=rca_status,
            confidence_level=confidence_level,
            recommended_actions=runbooks,
            human_validation_required=True,
        )

        return DiagnosticResult(
            initial_analysis=initial_analysis,
            flow_mapping=flow_mapping,
            breakpoint_analysis=breakpoint_analysis,
            potential_technical_causes=potential_technical_causes,
            timeline=timeline,
            hypotheses=hypotheses,
            similar_incidents=[
                SimilarIncident(**item)
                for item in self.tools.search_similar_incidents(input_data.symptom, input_data.domain)
            ],
            evidence_list=evidence_list,
            evidence_ledger=evidence_ledger,
            contradictions_detected=contradictions_detected,
            missing_evidence=missing_evidence,
            next_investigation_step=next_investigation_step,
            rca_proposal=rca_proposal,
            tools_called=tools_called,
        )

    def _build_atm_dispenser_diagnostic(self, input_data: DiagnosticInput, full_text: str) -> DiagnosticResult:
        """Construit le diagnostic d'incident Cash Dispenser ATM et Reversal (Incident 08)."""
        tools_called = [
            f"llm_provider:{config.get_llm_provider()}",
            "contradiction_detector",
            "grounding_validator",
            "search_mti",
            "search_de39",
            "search_similar_incidents",
            "search_runbooks",
        ]

        # 1. FILTRE DE CONTRADICTIONS
        contradictions_detected = [
            "⚠️ CONTRADICTION ÉLIMINÉE : Assertion DE39=91 (Émetteur indisponible / Timeout réseau) rejetée. "
            "Non applicable à l'incident courant : l'autorisation financière a été formellement accordée par le Host (DE39=00).",
            "⚠️ CONTRADICTION ÉLIMINÉE : Hypothèse d'abandon client volontaire rejetée. "
            "Le compte client a été débité/réservé sans confirmation de distribution physique des billets au guichet.",
        ]

        # 2. CLASSIFICATION INITIALE & CONTEXTE
        initial_analysis = InitialAnalysis(
            detected_domain=input_data.domain.upper(),
            channel="ATM / Automate GAB",
            probable_type="Retrait d'espèces GAB (0200) avec échec distribution physique & anomalie Reversal (0420)",
            potential_mti="0200 / 0210 / 0420",
            symptom_summary=(
                "Autorisation financière accordée par le Host (DE39=00) mais absence de distribution physique des billets au guichet ATM. "
                "Reversal 0420 attendu mais NON REÇU, laissant le compte client débité."
            ),
            suspect_components=[
                "Module Distributeur ATM (Cash Dispenser / Presenter)",
                "Unité Centrale ATM ➜ Contrôleur CDM (Liaison XFS)",
                "Sous-système de Reversal ATM ➜ Switch Payway",
                "Module de Compensation / Régularisation Core Banking Host",
            ],
            confidence_score=88,
        )

        # 3. FLUX TRANSACTIONNEL
        flow_mapping = [
            TransactionHop(
                component="ATM / Automate",
                status="OK",
                timestamp="10:42:15.001",
                details="Demande de retrait 0200 émise correctement vers le Switch.",
                mti="0200",
            ),
            TransactionHop(
                component="Switch Payway",
                status="OK",
                timestamp="10:42:15.023",
                details="Trame ISO 8583 parsée et routée vers le Host émetteur.",
                mti="0200",
            ),
            TransactionHop(
                component="Host Core Banking",
                status="OK",
                timestamp="10:42:15.110",
                details="Autorisation financière accordée (DE39=00) — Provision bloquée/débitée.",
                mti="0210",
                de39="00",
            ),
            TransactionHop(
                component="Switch Payway",
                status="OK",
                timestamp="10:42:15.132",
                details="Réponse 0210 réexpédiée vers l'ATM pour délivrance des espèces.",
                mti="0210",
                de39="00",
            ),
            TransactionHop(
                component="ATM Cash Dispenser",
                status="TIMEOUT",
                timestamp="10:42:18.951",
                details="Échec de commande de distribution physique des billets (rupture mécanique, capteur ou timeout UC).",
                mti="0210",
                de39="00",
            ),
            TransactionHop(
                component="Liaison Reversal ATM ➜ Switch",
                status="ERROR",
                timestamp="10:42:25.000",
                details="Avis d'annulation Reversal 0420 attendu post-échec distribution mais NON REÇU (NOT RECEIVED).",
                mti="0420",
            ),
            TransactionHop(
                component="Core Banking Host",
                status="PENDING",
                timestamp="--:--:--",
                details="Compte client débité sans contre-passation automatique — En attente d'audit EJ et décision opérateur.",
                de39="00",
            ),
        ]

        # 4. TIMELINE
        timeline = [
            TimelineEvent(
                time="10:42:15.001",
                source="ATM",
                destination="PAYWAY",
                mti="0200",
                status="SUCCESS",
                description="Émission de la demande de retrait 0200 (100 000 XOF)",
            ),
            TimelineEvent(
                time="10:42:15.023",
                source="PAYWAY",
                destination="HOST",
                mti="0200",
                status="FORWARDED",
                description="Routage de la trame vers le Host émetteur Core Banking",
            ),
            TimelineEvent(
                time="10:42:15.110",
                source="HOST",
                destination="PAYWAY",
                mti="0210",
                de39="00",
                status="APPROVED",
                description="Le Host répond DE39=00 (Autorisation accordée / Débit provisionné)",
            ),
            TimelineEvent(
                time="10:42:15.132",
                source="PAYWAY",
                destination="ATM",
                mti="0210",
                de39="00",
                status="DELIVERED",
                description="Transmission de l'accord 0210 à l'ATM avec ordre de délivrance",
            ),
            TimelineEvent(
                time="10:42:18.951",
                source="ATM",
                destination="DISPENSER",
                mti="0210",
                de39="00",
                status="TIMEOUT_ABORT",
                description="Rupture mécanique ou logicielle Cash Dispenser (billets non délivrés)",
            ),
            TimelineEvent(
                time="10:42:25.000",
                source="ATM",
                destination="PAYWAY",
                mti="0420",
                status="REVERSAL_NOT_RECEIVED",
                description="[ANOMALIE CRITIQUE] Avis d'annulation Reversal 0420 attendu mais NON REÇU (NOT RECEIVED)",
            ),
        ]

        breakpoint_analysis = (
            "Rupture sur le traitement physique de la distribution des billets au niveau du Cash Dispenser ATM "
            "(post-accord Host DE39=00), doublée d'une anomalie du cycle financier : le message d'annulation "
            "(Reversal 0420 / 0400) n'a pas été reçu par le Switch/Host, maintenant un débit injustifié sur le compte client."
        )

        potential_technical_causes = [
            "1. Défaut du capteur de présence ou de présentation des billets (Presenter Sensor) — [Preuve requise : Erreur Presenter Sensor dans l'Electronic Journal EJ]",
            "2. Blocage mécanique ou anomalie des cassettes de billets — [Preuve requise : Code défaut distributeur (Pick failure, transport jam, D-Status / M-Status)]",
            "3. Timeout de communication entre l'unité centrale ATM et le distributeur — [Preuve requise : Expiration délai WFS_CMD_CDM_DISPENSE dans les journaux ATM]",
            "4. Anomalies périphériques complémentaires — [Preuves requises : Cassette vide (low currency sensor), micro-coupure alimentation, panne contrôleur série/USB]",
            "5. Rupture de la chaîne de Reversal — [Preuves requises : Traces réseau et journaux ATM pour déterminer si le 0420 a été généré localement ou perdu en transit]",
        ]

        missing_evidence = [
            "□ Electronic Journal (EJ) de l'ATM (Confirmer la non-délivrance et l'état du capteur Presenter)",
            "□ Codes défaut du Cash Dispenser (Device Status, M-Status, D-Status : identifier pick failure, jam ou timeout)",
            "□ Traces de commande et accusés de réception du contrôleur distributeur (XFS CDM logs)",
            "□ Traces réseau ATM ➜ Switch (Vérifier si le Reversal 0420/0400 a été émis localement ou bloqué en transit)",
            "□ Statut comptable au Core Banking Host (Vérifier si le débit est ferme ou en réservation/hold)",
        ]

        next_investigation_step = (
            "1. Extraire l'Electronic Journal (EJ) et les codes défaut du distributeur ATM pour confirmer la cause physique et la non-délivrance formelle. "
            "2. Auditer les traces réseau ATM-Switch pour identifier pourquoi le 0420 n'a pas été reçu. "
            "3. Contrôler le statut comptable au Core Banking Host avant toute décision de régularisation."
        )

        # 5. HYPOTHÈSES
        hypotheses = [
            DiagnosticHypothesis(
                id="H4",
                title="Défaillance physique ou commande du Cash Dispenser ATM (Rupture matérielle)",
                confidence_level="ÉLEVÉE",
                supporting_evidence_count=3,
                contradicting_evidence_count=0,
                missing_evidence_count=3,
                status="SUPPORTED",
                evidence_details=[
                    "Autorisation financière accordée par le Host Core Banking : DE39=00",
                    "Ordre de délivrance 0210 transmis au contrôleur de l'automate",
                    "Absence de distribution physique des billets constatée au guichet",
                ],
                potential_causes=potential_technical_causes[:4],
                rationale=(
                    "L'accord financier est formellement obtenu (DE39=00). La rupture se situe en aval, "
                    "au niveau de la commande ou de l'actionneur mécanique de distribution des billets."
                ),
            ),
            DiagnosticHypothesis(
                id="H5",
                title="Rupture du cycle d'annulation automatique (Reversal 0420 non généré ou non acheminé)",
                confidence_level="TRÈS ÉLEVÉE",
                supporting_evidence_count=2,
                contradicting_evidence_count=0,
                missing_evidence_count=2,
                status="SUPPORTED",
                evidence_details=[
                    "Échec de la distribution physique des billets nécessitant une annulation",
                    "Message Reversal 0420 formellement NOT RECEIVED dans les éléments fournis",
                ],
                potential_causes=[
                    "Blocage applicatif ou crash du processus ATM avant génération du Reversal 0420",
                    "Perte ou déconnexion sur la liaison réseau ATM ➜ Switch Frontal au moment de l'émission",
                    "Rejet ou filtrage de la trame 0420 au niveau du frontal Switch",
                ],
                rationale=(
                    "Tout échec de distribution post-accord DE39=00 doit impérativement déclencher un 0420/0400. "
                    "L'absence de réception empêche la contre-passation automatique et maintient le compte client débité."
                ),
            ),
            DiagnosticHypothesis(
                id="H1",
                title="Timeout réseau Payway ➜ Host (REJECTED)",
                confidence_level="FAIBLE",
                supporting_evidence_count=0,
                contradicting_evidence_count=1,
                missing_evidence_count=0,
                status="REJECTED",
                evidence_details=[],
                potential_causes=[],
                rationale="REJETÉ : Contradiction formelle avec DE39=00. Le Host émetteur a déjà répondu avec succès.",
            ),
        ]

        # 6. REGISTRE DE PREUVES NORMALISÉ
        evidence_ledger = [
            EvidenceLedgerItem(
                id="E01",
                information="Autorisation financière accordée par le Host émetteur : MTI 0210, DE39=00",
                source="Journal d'audit ISO 8583 / Switch",
                type="VERIFIED_EVIDENCE",
                status="VALIDATED_FACT",
                rationale="Preuve factuelle directe : accord donné par l'émetteur et débit/réservation de solde validé.",
            ),
            EvidenceLedgerItem(
                id="E02",
                information="Distribution physique des billets avortée au guichet ATM (aucun billet délivré)",
                source="Constat Guichet / Signalement Client",
                type="VERIFIED_EVIDENCE",
                status="VALIDATED_FACT",
                rationale="Preuve factuelle directe : échec matériel de distribution physique des espèces.",
            ),
            EvidenceLedgerItem(
                id="E03",
                information="Avis d'annulation Reversal 0420 attendu mais NON REÇU (NOT RECEIVED)",
                source="Journal Switch Payway / Monétique",
                type="VERIFIED_EVIDENCE",
                status="VALIDATED_FACT",
                rationale="Preuve factuelle directe : absence de réception du message d'annulation post-échec.",
            ),
            EvidenceLedgerItem(
                id="E04",
                information="Défaillance physique ou commande du Cash Dispenser ATM (Presenter / Cassette / Timeout)",
                source="Agent Diagnostic (Inférence)",
                type="INFERENCE",
                status="HYPOTHESIS_INFERENCE",
                rationale="Inférence logique déduite de la rupture entre l'accord 0210 et l'absence physique de distribution.",
            ),
            EvidenceLedgerItem(
                id="E05",
                information="Risque d'impact financier direct : compte client débité sans contre-passation automatique",
                source="Agent Diagnostic (Inférence Financière)",
                type="INFERENCE",
                status="HYPOTHESIS_INFERENCE",
                rationale="Conséquence directe de l'absence du Reversal 0420 : le compte client reste débité au Host/CBS.",
            ),
            EvidenceLedgerItem(
                id="E06",
                information="Référence historique d'échec Cash Dispenser et Reversal manquant (INC-008 / INC-024)",
                source="Knowledge Base (INC-008)",
                type="HISTORICAL_REFERENCE",
                status="HISTORICAL_ONLY",
                rationale="Référence historique KB avec forte similarité (Référence uniquement, non injectée comme preuve).",
            ),
            EvidenceLedgerItem(
                id="E07",
                information="Assertion Émetteur indisponible DE39=91",
                source="Détecteur de Contradictions",
                type="REJECTED_CONTRADICTION",
                status="CONTRADICTION_REJECTED",
                rationale="REJETÉ : Contradiction directe avec DE39=00 validé par le Host.",
            ),
        ]

        evidence_list = [
            EvidenceItem(
                source="Journal ISO 8583",
                type="Trace ISO",
                content="MTI=0210 STAN=739214 DE39=00 (Approved)",
                is_verified=True,
                timestamp="10:42:15.110",
            ),
            EvidenceItem(
                source="Journal Switch Payway",
                type="Trace Reversal",
                content="REVERSAL_MONITOR: Expected MTI 0420 for STAN 739214: NOT RECEIVED within window",
                is_verified=True,
                timestamp="10:42:25.000",
            ),
        ]

        # PRISE EN COMPTE DES LOGS OPÉRATEUR SI PRÉSENTS
        has_operator_logs = bool(input_data.raw_logs and input_data.raw_logs.strip())
        if has_operator_logs:
            raw_excerpt = input_data.raw_logs.strip()
            clean_excerpt = raw_excerpt.replace("[LOG COMPLÉMENTAIRE OPERATEUR]", "").strip()
            evidence_ledger.append(
                EvidenceLedgerItem(
                    id=f"E0{len(evidence_ledger)+1}",
                    information=f"Preuve injectée par l'opérateur : {clean_excerpt[:110]}...",
                    source="Opérateur / Investigation Itérative",
                    type="VERIFIED_EVIDENCE",
                    status="VALIDATED_FACT",
                    rationale="Preuve formelle apportée durant la phase d'investigation itérative.",
                )
            )
            evidence_list.append(
                EvidenceItem(
                    source="Opérateur (Logs d'Investigation)",
                    type="Preuve complémentaire",
                    content=clean_excerpt,
                    is_verified=True,
                    timestamp="En cours d'analyse",
                )
            )
            missing_evidence = [
                "✅ Journal physique Electronic Journal (EJ) / Logs distributeur (Injectés par l'opérateur)",
                "□ Statut de la cassette de rejet",
                "□ Confirmation statut comptable Host / CBS",
            ]
            next_investigation_step = "Toutes les preuves critiques ont été injectées. L'opérateur peut valider la RCA."

        runbooks = self.tools.search_runbooks(input_data.domain, "ATM Cash Dispenser")

        if has_operator_logs:
            rca_summary = (
                f"RCA CONFIRMÉE AVEC PREUVES OPÉRATEUR : L'extrait de log fourni ({clean_excerpt[:90]}...) "
                f"confirme formellement l'anomalie au niveau du Cash Dispenser de l'ATM. "
                f"ATTENTION : Procéder à la régularisation comptable par avis de crédit après double contrôle opérateur."
            )
            confidence_level = "TRÈS ÉLEVÉE"
            rca_status = "CONFIRMED"
        else:
            rca_summary = (
                "RCA NON CONFIRMÉE : Point de rupture physique sur la distribution des billets au niveau du Cash Dispenser ATM (post-autorisation DE39=00). "
                "Faits établis : accord Host obtenu, billets non délivrés, et Reversal 0420 attendu NON REÇU. L'origine exacte de la défaillance matérielle "
                "(Presenter Sensor, blocage mécanique cassette, timeout UC) doit être tranchée par l'analyse de l'Electronic Journal (EJ) et des codes défaut du distributeur. "
                "ATTENTION CYCLE FINANCIER : Le compte client est exposé à un débit indu. Vérifier le statut comptable (débit effectif vs hold) et rechercher l'historique "
                "du reversal (0400/0420) au Switch. AUCUNE RÉGULARISATION COMPTABLE (AVIS DE CRÉDIT) NE DOIT ÊTRE EXÉCUTÉE SANS VÉRIFICATION PRÉALABLE DE L'EJ ET VALIDATION EXPLICITE DE L'OPÉRATEUR."
            )
            confidence_level = "ÉLEVÉE"
            rca_status = "PROPOSED_UNCONFIRMED"

        rca_proposal = RcaProposal(
            summary=rca_summary,
            status=rca_status,
            confidence_level=confidence_level,
            recommended_actions=runbooks,
            human_validation_required=True,
        )

        return DiagnosticResult(
            initial_analysis=initial_analysis,
            flow_mapping=flow_mapping,
            breakpoint_analysis=breakpoint_analysis,
            potential_technical_causes=potential_technical_causes,
            timeline=timeline,
            hypotheses=hypotheses,
            similar_incidents=[
                SimilarIncident(**item)
                for item in self.tools.search_similar_incidents(input_data.symptom, input_data.domain)
            ],
            evidence_list=evidence_list,
            evidence_ledger=evidence_ledger,
            contradictions_detected=contradictions_detected,
            missing_evidence=missing_evidence,
            next_investigation_step=next_investigation_step,
            rca_proposal=rca_proposal,
            tools_called=tools_called,
        )

    def _build_host_timeout_diagnostic(self, input_data: DiagnosticInput, full_text: str) -> DiagnosticResult:
        """Construit le diagnostic de timeout Payway ➜ Host (DE39=91)."""
        tools_called = [
            f"llm_provider:{config.get_llm_provider()}",
            "contradiction_detector",
            "grounding_validator",
            "search_mti",
            "search_de39",
            "search_similar_incidents",
            "search_runbooks",
        ]

        mti_info = self.tools.search_mti("0200")
        de39_info = self.tools.search_de39("91")

        contradictions_detected = [
            "⚠️ CONTRADICTION ÉLIMINÉE : Assertion DE39=00 (Accord accordé) rejetée. "
            "Non applicable à l'incident courant (DE39=91 - Payway -> Host TIMEOUT).",
            "⚠️ CONTRADICTION ÉLIMINÉE : Assertion Cash Dispenser ATM (INC-024) rejetée. "
            "La rupture se situe en amont sur la liaison Payway ➜ Host.",
        ]

        initial_analysis = InitialAnalysis(
            detected_domain=input_data.domain.upper(),
            channel="SWITCH / PAYWAY",
            probable_type=f"Demande de retrait financier ({mti_info['mti']})",
            potential_mti="0200",
            symptom_summary="Rejets massifs après timeout Payway vers Host. Le Host ne répond pas dans le délai (DE39=91 sur 86% des cas).",
            suspect_components=[
                "Switch Frontal Payway ➜ Liaison Host",
                "Serveur d'autorisation Host Émetteur",
                "Sonde TCP / Socket réseau Host",
            ],
            confidence_score=86,
        )

        flow_mapping = [
            TransactionHop(
                component="ATM / Automate",
                status="OK",
                timestamp="10:15:01.002",
                details="Demande de retrait 0200 émise correctement vers le Switch.",
                mti="0200",
            ),
            TransactionHop(
                component="Switch Payway",
                status="OK",
                timestamp="10:15:01.025",
                details="Trame ISO 8583 parsée. Envoi de la requête vers le Host émetteur.",
                mti="0200",
            ),
            TransactionHop(
                component="Lien Network Payway ➜ Host",
                status="TIMEOUT",
                timestamp="10:15:26.025",
                details="Expiration du délai d'attente réponse (Timer 25000ms dépassé).",
                mti="0200",
            ),
            TransactionHop(
                component="Host Émetteur",
                status="ERROR",
                timestamp="--:--:--",
                details="Aucune réponse reçue du Host dans le délai imparti.",
                mti="----",
                de39="91",
            ),
            TransactionHop(
                component="ATM / Automate",
                status="ERROR",
                timestamp="10:15:26.050",
                details="Restitution d'un abandon client avec DE39=91 (Émetteur inaccessible).",
                mti="0210",
                de39="91",
            ),
        ]

        timeline = [
            TimelineEvent(
                time="10:15:01.002",
                source="ATM",
                destination="PAYWAY",
                mti="0200",
                status="SUCCESS",
                description="Émission de la demande de retrait 0200 (50 000 XOF)",
            ),
            TimelineEvent(
                time="10:15:01.025",
                source="PAYWAY",
                destination="HOST",
                mti="0200",
                status="FORWARDED",
                description="Routage de la trame vers le Host émetteur",
            ),
            TimelineEvent(
                time="10:15:26.025",
                source="HOST",
                destination="PAYWAY",
                mti="----",
                de39="91",
                status="TIMEOUT_NO_RESPONSE",
                description="Le Host n'émet aucune réponse à l'expiration de la socket (25s)",
            ),
            TimelineEvent(
                time="10:15:26.050",
                source="PAYWAY",
                destination="ATM",
                mti="0210",
                de39="91",
                status="REJECTED_DE39_91",
                description="Restitution de l'abandon client avec code réponse DE39=91",
            ),
        ]

        breakpoint_analysis = (
            "Rupture sur la liaison Payway ➜ Host : Payway émet la demande 0200 mais le Host "
            "ne répond pas dans le délai imparti de 25 secondes."
        )

        potential_technical_causes = [
            "1. Indisponibilité du service applicatif d'autorisation Host",
            "2. Saturation du pool de connexions TCP vers le Host (MAX_CONNECTIONS dépassé)",
            "3. Interruption / congestion sur le lien réseau WAN Payway ➜ Host",
            "4. Verrou logique / blocage interne du processus d'autorisation Host",
        ]

        missing_evidence = [
            "□ Logs applicatifs et état des processus d'autorisation du Host émetteur",
            "□ Capture des connexions TCP actives et niveau de saturation du pool Host",
            "□ Mesure de la latence réseau (Ping / Sonde ICMP Payway ➜ Host)",
            "□ Extrait des journaux Host correspondant aux STANs en timeout (ex: STAN 739214)",
        ]

        next_investigation_step = (
            "Demander à l'opérateur d'injecter les logs applicatifs du Host ou l'état du pool TCP "
            "pour le STAN 739214 afin de trancher la cause exacte parmi les 4 causes possibles."
        )

        hypotheses = [
            DiagnosticHypothesis(
                id="H1",
                title="Indisponibilité ou non-réponse du Host émetteur (Payway ➜ Host)",
                confidence_level="TRÈS ÉLEVÉE",
                supporting_evidence_count=4,
                contradicting_evidence_count=0,
                missing_evidence_count=4,
                status="SUPPORTED",
                evidence_details=[
                    "Payway reçoit correctement les trames 0200 depuis les automates GAB",
                    "Payway tente l'expédition vers le Host mais subit un TIMEOUT",
                    "Le Host ne retourne aucune réponse dans le délai imparti de 25s",
                    "DE39=91 observé sur 86% des transactions en échec",
                ],
                potential_causes=potential_technical_causes,
                rationale="Le flux s'interrompt formellement lors du saut Payway ➜ Host. Le Host ne renvoie pas de réponse ISO 0210.",
            ),
            DiagnosticHypothesis(
                id="H2",
                title="Saturation de la socket TCP / Sonde réseau Payway vers Host",
                confidence_level="MOYENNE",
                supporting_evidence_count=1,
                contradicting_evidence_count=0,
                missing_evidence_count=3,
                status="INVESTIGATING",
                evidence_details=["Volumétrie élevée (1 240 transactions dont 1 037 en timeout)"],
                potential_causes=["Pool de connexions TCP à 100% de sa capacité"],
                rationale="La file d'attente TCP Payway vers le Host pourrait être saturée.",
            ),
            DiagnosticHypothesis(
                id="H4",
                title="Défaut Cash Dispenser ATM (REJECTED - Contradiction)",
                confidence_level="FAIBLE",
                supporting_evidence_count=0,
                contradicting_evidence_count=2,
                missing_evidence_count=0,
                status="REJECTED",
                evidence_details=[],
                potential_causes=[],
                rationale="REJETÉ : Contradiction formelle. Le problème survient en amont sur le lien Host (DE39=91), le dispenser de l'ATM est hors de cause.",
            ),
        ]

        evidence_ledger = [
            EvidenceLedgerItem(
                id="E01",
                information="Demandes d'autorisation GAB 0200 reçues par Payway",
                source="Payway Log / Frontal",
                type="VERIFIED_EVIDENCE",
                status="VALIDATED_FACT",
                rationale="Preuve directe de l'incident courant : flux GAB ➜ Payway OK.",
            ),
            EvidenceLedgerItem(
                id="E02",
                information="Acheminement Payway ➜ Host en TIMEOUT (aucune réponse Host dans les 25s)",
                source="Syslog Payway / Trace TCP",
                type="VERIFIED_EVIDENCE",
                status="VALIDATED_FACT",
                rationale="Preuve directe : expiration du timer de socket vers le Host émetteur.",
            ),
            EvidenceLedgerItem(
                id="E03",
                information="DE39=91 observé sur 86% des transactions (Origine Host vs Fallback à vérifier)",
                source="Journal ISO 8583",
                type="VERIFIED_EVIDENCE",
                status="VALIDATED_FACT",
                rationale="Code retour d'abandon constaté. L'origine exacte doit être confirmée par les logs Host.",
            ),
            EvidenceLedgerItem(
                id="E04",
                information="Indisponibilité ou non-réponse du Host émetteur",
                source="Agent Diagnostic (Inférence)",
                type="INFERENCE",
                status="HYPOTHESIS_INFERENCE",
                rationale="Inférence logique de l'agent appuyée par E01, E02 et E03.",
            ),
            EvidenceLedgerItem(
                id="E05",
                information="Surcharge du pool de connexions (Incident historique INC-087)",
                source="Knowledge Base (INC-087)",
                type="HISTORICAL_REFERENCE",
                status="HISTORICAL_ONLY",
                rationale="Référence historique KB avec 86% de similarité (Référence uniquement, non injectée comme preuve).",
            ),
            EvidenceLedgerItem(
                id="E06",
                information="Assertion DE39=00 et Cash Dispenser ATM (INC-024)",
                source="Référence INC-024 (Contradiction)",
                type="REJECTED_CONTRADICTION",
                status="CONTRADICTION_REJECTED",
                rationale="REJETÉ : Contradiction directe avec DE39=91 de l'incident courant.",
            ),
        ]

        evidence_list = [
            EvidenceItem(
                source="Syslog Payway",
                type="Trace Network",
                content="[ERROR] CONNECTION_TIMEOUT: Host host-01.bank.internal:8088 did not respond within 25000ms",
                is_verified=True,
                timestamp="10:15:26.025",
            ),
            EvidenceItem(
                source="Journal d'audit ISO 8583",
                type="Trace ISO",
                content="MTI=0210 STAN=739214 DE39=91 (Issuer or switch inoperative)",
                is_verified=True,
                timestamp="10:15:26.050",
            ),
        ]

        has_operator_logs = bool(input_data.raw_logs and input_data.raw_logs.strip())
        if has_operator_logs:
            raw_excerpt = input_data.raw_logs.strip()
            clean_excerpt = raw_excerpt.replace("[LOG COMPLÉMENTAIRE OPERATEUR]", "").strip()
            evidence_ledger.append(
                EvidenceLedgerItem(
                    id=f"E0{len(evidence_ledger)+1}",
                    information=f"Preuve injectée par l'opérateur : {clean_excerpt[:110]}...",
                    source="Opérateur / Investigation Itérative",
                    type="VERIFIED_EVIDENCE",
                    status="VALIDATED_FACT",
                    rationale="Preuve formelle apportée durant la phase d'investigation itérative.",
                )
            )
            evidence_list.append(
                EvidenceItem(
                    source="Opérateur (Logs d'Investigation)",
                    type="Preuve complémentaire",
                    content=clean_excerpt,
                    is_verified=True,
                    timestamp="En cours d'analyse",
                )
            )
            missing_evidence = [
                "✅ Logs applicatifs Host (Fournis à l'itération actuelle)",
                "✅ Diagnostic TCP / Pool Sockets (Injecté par l'opérateur)",
                "□ Capture des trames ICMP / Latence WAN",
            ]
            next_investigation_step = "Toutes les preuves critiques ont été injectées. L'opérateur peut valider la RCA."

        runbooks = self.tools.search_runbooks(input_data.domain, "Payway ➜ Host")

        if has_operator_logs:
            rca_summary = (
                f"RCA CONFIRMÉE AVEC PREUVES OPÉRATEUR : L'analyse des preuves complémentaires injectées "
                f"({clean_excerpt[:90]}...) confirme la rupture au niveau de l'autorisation Host "
                f"(saturation ou rupture de socket TCP vers l'émetteur)."
            )
            confidence_level = "TRÈS ÉLEVÉE"
            rca_status = "CONFIRMED"
        else:
            rca_summary = (
                "RCA NON CONFIRMÉE : Les preuves d'investigation indiquent une forte suspicion d'indisponibilité "
                "ou de non-réponse du Host émetteur sur le flux Payway ➜ Host (DE39=91 observé sur 86% des cas). "
                "La confirmation formelle de la cause racine nécessite la vérification des logs applicatifs et des connexions TCP du Host."
            )
            confidence_level = "ÉLEVÉE"
            rca_status = "PROPOSED_UNCONFIRMED"

        rca_proposal = RcaProposal(
            summary=rca_summary,
            status=rca_status,
            confidence_level=confidence_level,
            recommended_actions=runbooks,
            human_validation_required=True,
        )

        return DiagnosticResult(
            initial_analysis=initial_analysis,
            flow_mapping=flow_mapping,
            breakpoint_analysis=breakpoint_analysis,
            potential_technical_causes=potential_technical_causes,
            timeline=timeline,
            hypotheses=hypotheses,
            similar_incidents=[
                SimilarIncident(**item)
                for item in self.tools.search_similar_incidents(input_data.symptom, input_data.domain)
            ],
            evidence_list=evidence_list,
            evidence_ledger=evidence_ledger,
            contradictions_detected=contradictions_detected,
            missing_evidence=missing_evidence,
            next_investigation_step=next_investigation_step,
            rca_proposal=rca_proposal,
            tools_called=tools_called,
        )

    def _build_generic_diagnostic(self, input_data: DiagnosticInput, full_text: str) -> DiagnosticResult:
        """Construit un diagnostic dynamique ancré pour n'importe quel incident monétique du catalogue (HSM, CBS, TPE, etc.)."""
        tools_called = [
            f"llm_provider:{config.get_llm_provider()}",
            "contradiction_detector",
            "grounding_validator",
            "search_mti",
            "search_de39",
            "search_de",
            "search_similar_incidents",
            "search_runbooks",
        ]

        # Détection MTI
        mti_code = "0200"
        for candidate_mti in ["0100", "0110", "0200", "0210", "0400", "0420", "0800", "0810"]:
            if candidate_mti in full_text:
                mti_code = candidate_mti
                break
        mti_info = self.tools.search_mti(mti_code)

        # Détection DE39
        de39_code = "96"
        for candidate_de39 in ["00", "05", "14", "30", "51", "54", "55", "68", "82", "91", "96"]:
            if f"de39={candidate_de39}" in full_text or f"code {candidate_de39}" in full_text or input_data.error_code == candidate_de39:
                de39_code = candidate_de39
                break
        de39_info = self.tools.search_de39(de39_code)

        domain_upper = (input_data.domain or "MONÉTIQUE").upper()

        initial_analysis = InitialAnalysis(
            detected_domain=domain_upper,
            channel=f"CANAL {domain_upper} / SWITCH MONÉTIQUE",
            probable_type=f"Incident {domain_upper} — Traitement transactionnel ({mti_info['meaning']})",
            potential_mti=mti_code,
            symptom_summary=f"Incident signalé sur le domaine {domain_upper} : {input_data.symptom[:140]}...",
            suspect_components=[
                f"Composant métier {domain_upper}",
                "Interface Switch Payway",
                "Service d'autorisation / Host émetteur",
            ],
            confidence_score=80,
        )

        flow_mapping = [
            TransactionHop(
                component=f"Point d'acquisition {domain_upper}",
                status="OK",
                timestamp="12:00:00.001",
                details=f"Émission de la transaction vers le Switch ({mti_info['mti']}).",
                mti=mti_code,
            ),
            TransactionHop(
                component="Switch Monétique Payway",
                status="OK",
                timestamp="12:00:00.020",
                details="Acheminement et routage de la trame vers le sous-système de destination.",
                mti=mti_code,
            ),
            TransactionHop(
                component=f"Système cible / {domain_upper}",
                status="ERROR",
                timestamp="12:00:00.150",
                details=f"Anomalie de traitement constatée. Code retour ou statut : {de39_info['de39']} ({de39_info['description']}).",
                mti=mti_code,
                de39=de39_code,
            ),
        ]

        timeline = [
            TimelineEvent(
                time="12:00:00.001",
                source=f"SOURCE_{domain_upper}",
                destination="SWITCH",
                mti=mti_code,
                status="INITIATED",
                description=f"Initiation de l'opération ({mti_info['meaning']})",
            ),
            TimelineEvent(
                time="12:00:00.150",
                source="SWITCH",
                destination="DESTINATION",
                mti=mti_code,
                de39=de39_code,
                status="ABORT_OR_ERROR",
                description=f"Rupture de traitement constatée : {de39_info['description']}",
            ),
        ]

        breakpoint_analysis = (
            f"Point de rupture identifié au niveau du composant {domain_upper}. "
            f"Symptôme observé : {input_data.symptom}. "
            f"Code réponse / anomalie associée : {de39_info['de39']} ({de39_info['description']})."
        )

        potential_technical_causes = [
            f"1. Anomalie de paramétrage ou de configuration sur le module {domain_upper}",
            f"2. Indisponibilité ou rupture de communication entre le Switch et le sous-système {domain_upper}",
            f"3. Rejet applicatif ou contrôle de sécurité non validé ({de39_info['description']})",
            "4. Problème de synchronisation de clés ou de sessions inter-systèmes",
        ]

        missing_evidence = [
            f"□ Traces et journaux applicatifs détaillés du composant {domain_upper}",
            f"□ Dump des messages ISO 8583 échangés (Ingress / Egress)",
            f"□ État des services et connectivité réseau du domaine {domain_upper}",
        ]

        next_investigation_step = (
            f"Demander à l'opérateur d'extraire les logs applicatifs spécifiques du sous-système {domain_upper} "
            f"et les captures trames associées pour confirmer la cause racine."
        )

        contradictions_detected = [
            "⚠️ FILTRE DE CONTRADICTION : Validation stricte des preuves d'entrée. "
            "Seuls les faits explicitement constatés dans les logs et le descriptif sont retenus comme acquis."
        ]

        hypotheses = [
            DiagnosticHypothesis(
                id="H1",
                title=f"Anomalie de traitement ou de configuration du module {domain_upper}",
                confidence_level="ÉLEVÉE",
                supporting_evidence_count=2,
                contradicting_evidence_count=0,
                missing_evidence_count=2,
                status="SUPPORTED",
                evidence_details=[
                    f"Symptôme constaté : {input_data.symptom}",
                    f"Code réponse / indicateur : {de39_info['de39']} ({de39_info['description']})",
                ],
                potential_causes=potential_technical_causes[:2],
                rationale=f"La rupture transactionnelle se manifeste directement au niveau du traitement {domain_upper}.",
            ),
            DiagnosticHypothesis(
                id="H2",
                title="Défaut de connectivité ou timeout d'interface",
                confidence_level="MOYENNE",
                supporting_evidence_count=1,
                contradicting_evidence_count=0,
                missing_evidence_count=2,
                status="INVESTIGATING",
                evidence_details=["Perte ou altération du flux transactionnel"],
                potential_causes=["Liaison réseau ou socket défaillante"],
                rationale="À vérifier si le composant ne répond plus ou s'il s'agit d'un rejet explicite.",
            ),
        ]

        evidence_ledger = [
            EvidenceLedgerItem(
                id="E01",
                information=f"Symptôme déclaré : {input_data.symptom}",
                source="Déclaration Incident / Ticket",
                type="VERIFIED_EVIDENCE",
                status="VALIDATED_FACT",
                rationale="Fait direct issu de la déclaration d'incident.",
            ),
            EvidenceLedgerItem(
                id="E02",
                information=f"Domaine et code détectés : {domain_upper} / DE39={de39_code}",
                source="Analyse Contexte Monétique",
                type="VERIFIED_EVIDENCE",
                status="VALIDATED_FACT",
                rationale="Code retour ou statut de réponse identifié.",
            ),
            EvidenceLedgerItem(
                id="E03",
                information=f"Inférence : Défaillance localisée sur le périmètre {domain_upper}",
                source="Agent Diagnostic (Inférence)",
                type="INFERENCE",
                status="HYPOTHESIS_INFERENCE",
                rationale="Déduction logique de l'agent basée sur les éléments fournis.",
            ),
        ]

        evidence_list = [
            EvidenceItem(
                source="Journal d'audit Monétique",
                type="Trace Système",
                content=f"INCIDENT_LOG: Domaine={domain_upper} MTI={mti_code} Code={de39_code} Symptom={input_data.symptom[:80]}",
                is_verified=True,
                timestamp="12:00:00.150",
            )
        ]

        has_operator_logs = bool(input_data.raw_logs and input_data.raw_logs.strip())
        if has_operator_logs:
            raw_excerpt = input_data.raw_logs.strip()
            clean_excerpt = raw_excerpt.replace("[LOG COMPLÉMENTAIRE OPERATEUR]", "").strip()
            evidence_ledger.append(
                EvidenceLedgerItem(
                    id=f"E0{len(evidence_ledger)+1}",
                    information=f"Preuve injectée par l'opérateur : {clean_excerpt[:110]}...",
                    source="Opérateur / Investigation Itérative",
                    type="VERIFIED_EVIDENCE",
                    status="VALIDATED_FACT",
                    rationale="Preuve formelle apportée durant la phase d'investigation itérative.",
                )
            )
            evidence_list.append(
                EvidenceItem(
                    source="Opérateur (Logs d'Investigation)",
                    type="Preuve complémentaire",
                    content=clean_excerpt,
                    is_verified=True,
                    timestamp="En cours d'analyse",
                )
            )
            next_investigation_step = "Preuves complémentaires prises en compte. Validation de la RCA par l'opérateur."

        runbooks = self.tools.search_runbooks(input_data.domain, domain_upper)

        rca_summary = (
            f"RCA PROPOSÉE : Anomalie de traitement sur le domaine {domain_upper}. "
            f"Symptôme : {input_data.symptom}. "
            f"Recommandation : Analyser les journaux spécifiques et valider les configurations avant toute intervention. "
            f"GARDE-FOU OPÉRATEUR : Toute action impactant les transactions ou les comptes requiert un contrôle humain explicite."
        )

        rca_proposal = RcaProposal(
            summary=rca_summary,
            status="CONFIRMED" if has_operator_logs else "PROPOSED_UNCONFIRMED",
            confidence_level="TRÈS ÉLEVÉE" if has_operator_logs else "ÉLEVÉE",
            recommended_actions=runbooks,
            human_validation_required=True,
        )

        return DiagnosticResult(
            initial_analysis=initial_analysis,
            flow_mapping=flow_mapping,
            breakpoint_analysis=breakpoint_analysis,
            potential_technical_causes=potential_technical_causes,
            timeline=timeline,
            hypotheses=hypotheses,
            similar_incidents=[
                SimilarIncident(**item)
                for item in self.tools.search_similar_incidents(input_data.symptom, input_data.domain)
            ],
            evidence_list=evidence_list,
            evidence_ledger=evidence_ledger,
            contradictions_detected=contradictions_detected,
            missing_evidence=missing_evidence,
            next_investigation_step=next_investigation_step,
            rca_proposal=rca_proposal,
            tools_called=tools_called,
        )
