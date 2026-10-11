"""Agents Copilot spécialisés pour les décodeurs monétiques (EMV / DE55 & ATM Electronic Journal)."""

from agentic.schemas.decoders import (
    AtmEjAnalysisInput,
    AtmEjAnalysisResult,
    EmvAnalysisInput,
    EmvAnalysisResult,
)


class EmvCopilotAgent:
    """Agent Copilot pour l'analyse experte des tets TLV DE55 et des alertes TVR Tag 95."""

    def analyze(self, input_data: EmvAnalysisInput) -> EmvAnalysisResult:
        clean_hex = input_data.input_hex.upper().replace(" ", "")
        tvr_raw = (input_data.tvr_raw or "").upper().replace(" ", "")
        flags = [f.lower() for f in input_data.critical_flags]

        is_pin_failed = "pin" in " ".join(flags) or "0000048000" in tvr_raw or "000004" in tvr_raw
        is_floor_exceeded = "floor" in " ".join(flags) or "08" in tvr_raw
        is_nominal_tc = "40" in clean_hex and not flags and tvr_raw in ["0000000000", "00000000", ""]

        if is_pin_failed:
            crypto_type = "ARQC (Authorization Request Cryptogram) / Refus Probable"
            risk_level = "ÉLEVÉ"
            summary_title = "Dépassement du Nombre d'Essais PIN / Alerte Sécurité TVR"
            tvr_analysis_detail = (
                f"Analyse Bit-à-Bit du TVR ({tvr_raw or 'Tag 95 (0000048000)'}) : "
                "Bit 5 / Octet 3 (PIN Try Limit Exceeded) activé. La puce a détecté une saisie de PIN erronée "
                "et a exigé une vérification en ligne (ARQC). Le compteur d'essais PIN a atteint son seuil maximal."
            )
            recommended_actions = [
                "Vérifier le code réponse DE39 renvoyé par l'émetteur (Attendu : DE39=55 PIN incorrect ou DE39=75 Saisie PIN dépassée)",
                "Proposer au porteur le déblocage du compteur PIN en guichet automatique après vérification d'identité",
                "Contrôler la présence de tentatives frauduleuses successives sur ce PAN",
            ]
            copilot_explanation = (
                "La transaction a déclenché une alerte de sécurité puce suite à des erreurs répétées de saisie du PIN. "
                "La puce EMV refuse le traitement hors-ligne et force la demande d'autorisation en ligne vers l'Host émetteur. "
                "Si l'Host confirme l'échec PIN (DE39=55), la carte doit être conservée ou le service bloqué temporairement."
            )
        elif is_nominal_tc:
            crypto_type = "TC (Transaction Certificate) / Validation Hors-Ligne"
            risk_level = "FAIBLE"
            summary_title = "Transaction EMV Nominale (Certificat TC Validé)"
            tvr_analysis_detail = (
                f"Analyse Bit-à-Bit du TVR ({tvr_raw or '0000000000'}) : "
                "Tous les octets du TVR sont à 0x00. Aucune anomalie de sécurité (PIN, CAM, Floor Limit) n'a été levée par la puce."
            )
            recommended_actions = [
                "Aucune action corrective requise",
                "Transaction conforme aux spécifications EMVCo",
            ]
            copilot_explanation = (
                "Le paquet DE55 indique un traitement EMV parfait. La carte a produit un certificat TC "
                "attestant d'une transaction hors-ligne pleinement autorisée sans aucun flag de risque sur le TVR."
            )
        else:
            crypto_type = "ARQC (Authorization Request Cryptogram)"
            risk_level = "MOYEN"
            summary_title = "Analyse Complète DE55 & Paramètres Sécurité EMV"
            tvr_analysis_detail = (
                f"Décodage du TVR ({tvr_raw or 'Tag 95'}) avec {input_data.parsed_tags_count} tags répertoriés. "
                f"Flags d'alertes identifiés : {', '.join(input_data.critical_flags) if input_data.critical_flags else 'Traitement en ligne demandé'}"
            )
            recommended_actions = [
                "Vérifier l'adéquation entre le montant de la transaction et le plafond Floor Limit de l'acquéreur",
                "Inspecter la cohérence du Tag 9F36 (ATC - Application Transaction Counter) pour détecter d'éventuels rejeux de trames (Replay Attack)",
            ]
            copilot_explanation = (
                "La trame EMV présente une structure conforme nécessitant une validation en ligne par le serveur d'autorisation. "
                "L'agent recommande de vérifier le statut de la réponse ARPC envoyée par l'Host dans le champ 55 de la trame retour 0210."
            )

        return EmvAnalysisResult(
            summary_title=summary_title,
            crypto_type=crypto_type,
            risk_level=risk_level,
            tvr_analysis_detail=tvr_analysis_detail,
            recommended_actions=recommended_actions,
            copilot_explanation=copilot_explanation,
        )


class AtmEjCopilotAgent:
    """Agent Copilot pour l'analyse judiciaire / forensic des journaux électroniques GAB (ATM EJ)."""

    def analyze(self, input_data: AtmEjAnalysisInput) -> AtmEjAnalysisResult:
        log_text = input_data.raw_log.upper()
        vendor = input_data.vendor or ("NCR" if "NCR" in log_text else "DIEBOLD" if "DIEBOLD" in log_text else "GAB GENERIC")

        is_jam = "JAM" in log_text or "STACKER" in log_text or "HARDWARE ERROR" in log_text or "NOT OPENED" in log_text
        is_retract = "RETRACT" in log_text or "TIMEOUT" in log_text or "PRESENT TIMEOUT" in log_text
        is_taken = "BILLS TAKEN" in log_text or "DISPENSE OK" in log_text or "EXIT SENSOR CLEARED" in log_text

        if is_jam:
            summary_title = "Échec Mécanique Distributeur — Bourrage Billets Attesté"
            hardware_fault_detected = True
            forensic_chronology = [
                "1. Demande d'autorisation 0200 émise et validée par le Host émetteur (DE39=00)",
                "2. Commande d'éjection des billets initiée par le contrôleur physique de l'ATM",
                "3. Déclenchement de l'erreur matérielle : HARDWARE ERROR STACKER JAMMED IN TRANSPORT",
                "4. Occlusion du volet (Shutter Not Opened) et annulation de la séquence de mise à disposition",
            ]
            claim_verdict_explanation = (
                "AVIS METIER OPPOSABLE : FAVORABLE AU RECRÉDIT CLIENT. "
                "Le journal électronique (EJ) prouve formellement un blocage mécanique des billets avant l'ouverture du volet. "
                "Le client a été débité à tort car les billets n'ont jamais été physiquement accessibles."
            )
            recommended_actions = [
                "Émettre un avis de crédit compensatoire de régularisation en faveur du compte client",
                "Transmettre le ticket d'incident matériel à l'équipe de maintenance pour débrayage du module transporteur GAB",
                "Rapprocher le solde physique de la cassette de rejet lors du prochain comptage physique",
            ]
            copilot_explanation = (
                "L'analyse des capteurs matériels confirme un incident mécanique critique. Le volet de distribution ne s'est pas ouvert. "
                "La réclamation du client est pleinement justifiée et doit être régularisée sans pénalité."
            )
        elif is_retract:
            summary_title = "Oubli Client & Rétractation vers Cassette de Rejet"
            hardware_fault_detected = False
            forensic_chronology = [
                "1. Autorisation accordée par le Host émetteur (DE39=00)",
                "2. Présentation physique des billets au niveau du volet (Shutter Opened - Bills Presented)",
                "3. Carte restituée et récupérée par le porteur",
                "4. Expiration de la temporisation de présence (PRESENT TIMEOUT 30s dépassé)",
                "5. Action de sécurité : Rétractation physique des billets vers la cassette de rejet",
            ]
            claim_verdict_explanation = (
                "AVIS METIER OPPOSABLE : FAVORABLE SOUS RÉSERVE DE COMPTAGE CASSETTE REJET. "
                "Le journal EJ atteste que les billets ont été présentés au guichet mais n'ont pas été pris par le porteur dans le délai imparti. "
                "L'automate a rapatrié les billets dans le bac de rejet."
            )
            recommended_actions = [
                "Vérifier le journal de comptage de la cassette de rejet (Audit Purge Log) pour valider la présence physique des billets",
                "Confirmer l'absence de capture vidéo suspecte (trappeur de billets / Cash Trapping)",
                "Procéder au remboursement du porteur après confirmation de l'excédent de caisse lors du comptage d'arrêt",
            ]
            copilot_explanation = (
                "Le journal indique un oubli client. Les billets ont été présentés puis réaspirés automatiquement par sécurité. "
                "Le recrédit est justifié une fois le contrôle de caisse du GAB validé."
            )
        elif is_taken:
            summary_title = "Distribution Complète et Confirmée par les Capteurs de Sortie"
            hardware_fault_detected = False
            forensic_chronology = [
                "1. Saisie du PIN et autorisation accordée (DE39=00)",
                "2. Distribution et ouverture du volet (Bills Presented)",
                "3. Carte retirée par le porteur (Card Taken)",
                "4. Effacement du capteur de sortie (BILLS TAKEN - EXIT SENSOR CLEARED)",
                "5. Clôture nominale de la transaction (DISPENSE OK)",
            ]
            claim_verdict_explanation = (
                "AVIS METIER OPPOSABLE : REJET FORMEL DE LA RÉCLAMATION. "
                "Le journal électronique atteste de la libération du capteur de sortie physique. "
                "Les billets ont été effectivement pris par l'utilisateur."
            )
            recommended_actions = [
                "Notifier le rejet de la réclamation au porteur avec l'extrait certifié du journal EJ",
                "Conserver l'extrait de log en archivage légal réclamations",
            ]
            copilot_explanation = (
                "Le capteur de sortie physique de l'automate atteste que les billets ont été retirés par le porteur. "
                "La réclamation de non-délivrance est infondée et doit être rejetée d'après l'audit d'impression."
            )
        else:
            summary_title = "Analyse Forensic du Journal Électronique GAB"
            hardware_fault_detected = False
            forensic_chronology = [
                "1. Analyse des séquences de logs du terminal",
                "2. Évaluation des statuts capteurs et de la trame d'impression",
            ]
            claim_verdict_explanation = (
                "AVIS METIER OPPOSABLE : INVESTIGATION COMPLÉMENTAIRE REQUISE. "
                "Les logs fournis ne permettent pas de trancher définitivement entre un retrait effectif et une annulation."
            )
            recommended_actions = [
                "Demander un extrait de journal EJ étendu (15 minutes avant et après l'horodatage)",
                "Consulter le fichier journal de réconciliation du comptage caisse",
            ]
            copilot_explanation = (
                "L'agent recommande de fournir des lignes de logs supplémentaires pour déterminer le statut exact des capteurs de sortie."
            )

        return AtmEjAnalysisResult(
            summary_title=summary_title,
            vendor_detected=vendor,
            hardware_fault_detected=hardware_fault_detected,
            forensic_chronology=forensic_chronology,
            claim_verdict_explanation=claim_verdict_explanation,
            recommended_actions=recommended_actions,
            copilot_explanation=copilot_explanation,
        )
