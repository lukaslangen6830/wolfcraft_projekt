import numpy as np
import matplotlib.pyplot as plt

# ==========================================
# 1. WIRTSCHAFTLICHE PARAMETER
#    konservative Abschätzung
# ==========================================
preis_strom = 0.17      # €/kWh
volllaststunden = 2760  # h/a
zins = 0.08             # 8 % Kapitalzinssatz
jahre = 3               # 5 Jahre Amortisationszeit

# Annuitätenfaktor
annuitaet = (zins * (1 + zins)**jahre) / ((1 + zins)**jahre - 1)

# Kosten-Faktoren: Edelstahl-Plattenwärmeübertrager (Heizung, FriWa, Verdampfer)
a_fix_platte = 15000     # Fixkosten €
c_ref_platte = 30000    # Referenzkosten €
a_ref_platte = 50       # Referenzfläche m²
m_deg_platte = 0.71     # Degressionsexponent

# Kosten-Faktoren: Lamellen-Heizregister (Lufterhitzung für Granulattrocknung)
a_fix_luft = 10000       # Fixkosten €
c_ref_luft = 20000       # Referenzkosten €
a_ref_luft = 100        # Referenzfläche m²
m_deg_luft = 0.71       # Degressionsexponent

# ==========================================
# 2. THERMISCHE ANLAGENDATEN
# ==========================================
# Leistungen
Q_Heizung = 159.57      # kW
Q_Brauchw = 17.73       # kW
Q_Trockn  = 54.38       # kW
Q_Gesamt  = Q_Heizung + Q_Brauchw + Q_Trockn  # 231.68 kW

# k-Werte (Wärmedurchgangskoeffizienten in kW/m²K)
k_wasser = 1.5          # Platten-WÜ (Heizung, FriWa)
k_verdampf = 1.0        # Platten-WÜ (SGM-Wasser / R290)
k_luft = 0.03           # Lamellenrohr (Heizwasser / Trocknungsluft)

# =======================================================
# 3. HILFSFUNKTION FÜR LOGARITHMISCHE TEMPERATURDIFFERENZ 
# =======================================================
def calc_lmtd(dt_a, dt_b):
    """Berechnet die logarithmische Temperaturdifferenz"""
    if dt_a <= 0.1 or dt_b <= 0.1: 
        return 0.1 # Sicherheit gegen Division durch Null / negative Logs
    if abs(dt_a - dt_b) < 0.1:
        return (dt_a + dt_b) / 2 # Limes für dt_a -> dt_b
    return (dt_a - dt_b) / np.log(dt_a / dt_b)

# ==========================================
# 4. SUPERTARGETING SCHLEIFE
# ==========================================
delta_t_range = np.arange(1.0, 15.5, 0.5) # Array mit gleichen Abständen zwischen 1K und 15K in 0.5K Schritten

kosten_invest_jahr = []
kosten_betrieb_jahr = []
kosten_gesamt = []

for dT in delta_t_range:
    
    # --- WP TEMPERATUREN & COP ---
    # Heizungsvorlauf (45°C) zzgl. Delta T = Kondensation
    T_cond = 45.0 + dT
    # SGM-Wasser Austritt (18°C) abzgl. Delta T = Verdampfung
    T_evap = 18.0 - dT
    # Heißgas-Spitze (R290 Spezifikum, ca. 20K über Kondensation)
    T_hotgas = T_cond + 20.0
    
    # Realer COP (Gütegrad 0.5)
    carnot_cop = (T_cond + 273.15) / (T_cond - T_evap)
    real_cop = 0.5 * carnot_cop
    
    P_el = Q_Gesamt / real_cop
    Q_Kaelte = Q_Gesamt - P_el
    
    # --- LOGARITHMISCHE TEMPERATURDIFFERENZ & FLÄCHENBERECHNUNG ---
    # 1. Heizung (Symmetrischer Gegenstrom: 48°C->38°C und 45°C<-35°C)
    lmtd_heiz = dT 
    A_heiz = Q_Heizung / (k_wasser * lmtd_heiz)
    
    # 2. Verdampfer (SGM Wasser 24°C->18°C / R290 isotherm bei T_evap)
    lmtd_verd = calc_lmtd(24.0 - T_evap, 18.0 - T_evap)
    A_verd = Q_Kaelte / (k_verdampf * lmtd_verd)
    
    # 3. Frischwasserstation (Speicherwasser T_hotgas->20°C / Trinkwasser 60°C<-10°C)
    lmtd_friwa = calc_lmtd(T_hotgas - 60.0, 20.0 - 10.0)
    A_friwa = Q_Brauchw / (k_wasser * lmtd_friwa)
    
    # 4. Trocknungsluft (Speicherwasser T_hotgas->45°C / Luft 60°C<-20°C)
    lmtd_trock = calc_lmtd(T_hotgas - 60.0, 45.0 - 20.0)
    A_trock = Q_Trockn / (k_luft * lmtd_trock)
    
    # --- C. KOSTENBERECHNUNG ---
    Cost_Heiz = a_fix_platte + c_ref_platte * (A_heiz / a_ref_platte)**m_deg_platte
    Cost_Verd = a_fix_platte + c_ref_platte * (A_verd / a_ref_platte)**m_deg_platte
    Cost_FriWa = a_fix_platte + c_ref_platte * (A_friwa / a_ref_platte)**m_deg_platte
    Cost_Trock = a_fix_luft + c_ref_luft * (A_trock / a_ref_luft)**m_deg_luft
    
    invest_total = Cost_Heiz + Cost_Verd + Cost_FriWa + Cost_Trock
    capex_pa = invest_total * annuitaet
    kosten_invest_jahr.append(capex_pa)
    
    opex_pa = P_el * volllaststunden * preis_strom
    kosten_betrieb_jahr.append(opex_pa)
    
    kosten_gesamt.append(capex_pa + opex_pa)

# ==========================================
# 5. OPTIMUM FINDEN UND AUSWERTEN
# ==========================================
idx_opt = np.argmin(kosten_gesamt)
dT_opt = delta_t_range[idx_opt]

print(f"Optimales delta T_min:        {dT_opt} K")
print(f"Minimale jährliche Kosten:    {kosten_gesamt[idx_opt]:,.0f} €/a")
print(f"  davon Invest (4 Apparate):  {kosten_invest_jahr[idx_opt]:,.0f} €/a")
print(f"  davon Strom (Wärmepumpe):   {kosten_betrieb_jahr[idx_opt]:,.0f} €/a")

# ==========================================
# 6. DIAGRAMM ERSTELLEN
# ==========================================
plt.figure(figsize=(10, 6))
plt.plot(delta_t_range, kosten_invest_jahr, 'g-', linewidth=2, label='Investitionskosten, 4 WÜ)')
plt.plot(delta_t_range, kosten_betrieb_jahr, 'r-', linewidth=2, label='Stromkosten WP')
plt.plot(delta_t_range, kosten_gesamt, 'k-', linewidth=3, label='Jährliche Gesamtkosten')

plt.axvline(x=dT_opt, color='k', linestyle='--', alpha=0.5)
plt.plot(dT_opt, kosten_gesamt[idx_opt], 'ko', markersize=8)
plt.text(dT_opt + 0.3, kosten_gesamt[idx_opt]*1.05, f' Optimum:\n $\Delta T_{{min}} = {dT_opt}$ K')

plt.title('Supertargeting', fontsize=14)
plt.xlabel('Minimale Temperaturdifferenz $\Delta T_{min}$ (Heizungskondensator) [K]')
plt.ylabel('Kosten pro Jahr [€/a]')
plt.legend()
plt.grid(True, linestyle=':', alpha=0.7)
plt.tight_layout()
plt.show()