// Hand-written to match supabase/migrations/0001_full_schema.sql (the
// consolidated baseline that replaced the old 0001->0004 chain — see
// supabase/migrations/_archive_pre_reset/). Once it has run, regenerate with
// the Supabase CLI/MCP (`generate_typescript_types`) and replace this file.

export type ExamScheduleStatus = "scheduled" | "open" | "in_progress" | "closed" | "cancelled";

export type ExamSessionStatus = "started" | "terminated";

export type ExcelImportStatus = "en_cours" | "termine" | "erreur";

export type UserRole = "national" | "regional" | "complexe" | "etablissement" | "surveillant";

export interface Database {
  public: {
    Tables: {
      regions: {
        Row: { id: string; name: string };
        Insert: { id?: string; name: string };
        Update: { id?: string; name?: string };
      };
      // Complexe de Formation, between regions (DR) and etablissements (ET).
      complexes: {
        Row: {
          id: string;
          region_id: string;
          name: string;
          created_by: string | null;
          created_at: string;
        };
        Insert: {
          id?: string;
          region_id: string;
          name: string;
          created_by?: string | null;
          created_at?: string;
        };
        Update: Partial<Database["public"]["Tables"]["complexes"]["Insert"]>;
      };
      etablissements: {
        Row: {
          id: string;
          region_id: string;
          complexe_id: string | null;
          name: string;
          login: string;
          created_by: string | null;
          created_at: string;
        };
        Insert: {
          id?: string;
          region_id: string;
          complexe_id?: string | null;
          name: string;
          login: string;
          created_by?: string | null;
          created_at?: string;
        };
        Update: Partial<Database["public"]["Tables"]["etablissements"]["Insert"]>;
      };
      profiles: {
        Row: {
          id: string;
          role: UserRole;
          region_id: string | null;
          complexe_id: string | null;
          etablissement_id: string | null;
          full_name: string;
          is_active: boolean;
          login: string | null;
          created_at: string;
        };
        Insert: {
          id: string;
          role: UserRole;
          region_id?: string | null;
          complexe_id?: string | null;
          etablissement_id?: string | null;
          full_name: string;
          is_active?: boolean;
          login?: string | null;
          created_at?: string;
        };
        Update: Partial<Database["public"]["Tables"]["profiles"]["Insert"]>;
      };
      // The per-établissement/date schedule (distinct from exam_sessions
      // below, which is the per-candidate attempt).
      exam_schedules: {
        Row: {
          id: string;
          etablissement_id: string;
          exam_date: string;
          start_time: string;
          variant_mode: string;
          status: ExamScheduleStatus;
          room: string | null;
          duration_minutes: number | null;
          mos_version: string | null;
          nb_postes: number | null;
          created_by: string | null;
          created_at: string;
        };
        Insert: {
          id?: string;
          etablissement_id: string;
          exam_date: string;
          start_time: string;
          variant_mode?: string;
          status?: ExamScheduleStatus;
          room?: string | null;
          duration_minutes?: number | null;
          mos_version?: string | null;
          nb_postes?: number | null;
          created_by?: string | null;
          created_at?: string;
        };
        Update: Partial<Database["public"]["Tables"]["exam_schedules"]["Insert"]>;
      };
      // first_name/last_name/cin/birth_date/phone/sexe/filiere/groupe/
      // photo_path are read by exact name by the desktop kiosk — never
      // rename these. Everything else is the rest of the 30-column Excel
      // import spec.
      candidates: {
        Row: {
          id: string;
          etablissement_id: string;
          exam_schedule_id: string | null;
          first_name: string;
          last_name: string;
          cin: string;
          birth_date: string | null;
          phone: string | null;
          import_batch_id: string | null;
          sexe: string | null;
          filiere: string | null;
          groupe: string | null;
          photo_path: string | null;
          nom_arabe: string | null;
          prenom_arabe: string | null;
          prenom2: string | null;
          lieu_naissance: string | null;
          matricule_etudiant: string | null;
          diplome: string | null;
          code_diplome: string | null;
          libelle_long: string | null;
          principale: string | null;
          code: string | null;
          codediplome1: string | null;
          niveau_scolaire: string | null;
          annee_etude: string | null;
          etudiant_actif: boolean | null;
          etudiant_payant: boolean | null;
          regime_inscription: string | null;
          date_inscription: string | null;
          date_dossier_complet: string | null;
          motif_admission: string | null;
          site: string | null;
          n_tel_tuteur: string | null;
          adresse: string | null;
          nationalite: string | null;
          id_inscription_session: string | null;
          created_at: string;
        };
        Insert: {
          id?: string;
          etablissement_id: string;
          exam_schedule_id?: string | null;
          first_name: string;
          last_name: string;
          cin: string;
          birth_date?: string | null;
          phone?: string | null;
          import_batch_id?: string | null;
          sexe?: string | null;
          filiere?: string | null;
          groupe?: string | null;
          photo_path?: string | null;
          nom_arabe?: string | null;
          prenom_arabe?: string | null;
          prenom2?: string | null;
          lieu_naissance?: string | null;
          matricule_etudiant?: string | null;
          diplome?: string | null;
          code_diplome?: string | null;
          libelle_long?: string | null;
          principale?: string | null;
          code?: string | null;
          codediplome1?: string | null;
          niveau_scolaire?: string | null;
          annee_etude?: string | null;
          etudiant_actif?: boolean | null;
          etudiant_payant?: boolean | null;
          regime_inscription?: string | null;
          date_inscription?: string | null;
          date_dossier_complet?: string | null;
          motif_admission?: string | null;
          site?: string | null;
          n_tel_tuteur?: string | null;
          adresse?: string | null;
          nationalite?: string | null;
          id_inscription_session?: string | null;
          created_at?: string;
        };
        Update: Partial<Database["public"]["Tables"]["candidates"]["Insert"]>;
      };
      // Per-batch Excel import report (row counts + per-row errors_json),
      // referenced by candidates.import_batch_id.
      excel_imports: {
        Row: {
          id: string;
          etablissement_id: string;
          exam_schedule_id: string | null;
          nom_fichier: string | null;
          nb_lignes: number;
          nb_inseres: number;
          nb_doublons: number;
          nb_erreurs: number;
          statut: ExcelImportStatus;
          errors_json: Array<{ row: number; message: string }>;
          created_by: string | null;
          created_at: string;
        };
        Insert: {
          id?: string;
          etablissement_id: string;
          exam_schedule_id?: string | null;
          nom_fichier?: string | null;
          nb_lignes?: number;
          nb_inseres?: number;
          nb_doublons?: number;
          nb_erreurs?: number;
          statut?: ExcelImportStatus;
          errors_json?: Array<{ row: number; message: string }>;
          created_by?: string | null;
          created_at?: string;
        };
        Update: Partial<Database["public"]["Tables"]["excel_imports"]["Insert"]>;
      };
      // One row per candidate attempt — bridges the desktop kiosk to the
      // platform (distinct from exam_schedules above).
      exam_sessions: {
        Row: {
          id: string;
          candidate_id: string;
          exam_schedule_id: string;
          validated_by: string | null;
          validated_at: string | null;
          desktop_session_uuid: string | null;
          variant: string | null;
          score_pct: number | null;
          passed: boolean | null;
          started_at: string | null;
          ended_at: string | null;
          workstation: string | null;
          hostname: string | null;
          ip_local: string | null;
          incidents: Record<string, unknown> | null;
          technical_logs: Record<string, unknown> | null;
          task_results: Array<{ task_num: number | string; title: string; score: number; passed: boolean }> | null;
          status: ExamSessionStatus;
          synced_at: string;
        };
        Insert: {
          id?: string;
          candidate_id: string;
          exam_schedule_id: string;
          validated_by?: string | null;
          validated_at?: string | null;
          desktop_session_uuid?: string | null;
          variant?: string | null;
          score_pct?: number | null;
          passed?: boolean | null;
          started_at?: string | null;
          ended_at?: string | null;
          workstation?: string | null;
          hostname?: string | null;
          ip_local?: string | null;
          incidents?: Record<string, unknown> | null;
          technical_logs?: Record<string, unknown> | null;
          task_results?: Array<{ task_num: number | string; title: string; score: number; passed: boolean }> | null;
          status?: ExamSessionStatus;
          synced_at?: string;
        };
        Update: Partial<Database["public"]["Tables"]["exam_sessions"]["Insert"]>;
      };
      // Surveillant-reported incidents against a session slot.
      incident_reports: {
        Row: {
          id: string;
          type_incident: string | null;
          description: string;
          exam_schedule_id: string | null;
          reported_by: string | null;
          created_at: string;
        };
        Insert: {
          id?: string;
          type_incident?: string | null;
          description: string;
          exam_schedule_id?: string | null;
          reported_by?: string | null;
          created_at?: string;
        };
        Update: Partial<Database["public"]["Tables"]["incident_reports"]["Insert"]>;
      };
      audit_logs: {
        Row: {
          id: number;
          actor: string | null;
          candidate_id: string | null;
          etablissement_id: string | null;
          event: string;
          hostname: string | null;
          result: string | null;
          message: string | null;
          app_version: string | null;
          detail: Record<string, unknown> | null;
          created_at: string;
        };
        Insert: {
          id?: number;
          actor?: string | null;
          candidate_id?: string | null;
          etablissement_id?: string | null;
          event: string;
          hostname?: string | null;
          result?: string | null;
          message?: string | null;
          app_version?: string | null;
          detail?: Record<string, unknown> | null;
          created_at?: string;
        };
        Update: Partial<Database["public"]["Tables"]["audit_logs"]["Insert"]>;
      };
    };
  };
}
