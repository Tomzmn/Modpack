# Serveurs Minecraft de Tom

Chaque serveur a son **instance Prism** : un fichier à importer une seule fois. À chaque lancement,
elle réveille le serveur, met les mods à jour, puis connecte le jeu.

## Jouer en 4 étapes

1. **Installer [Prism Launcher](https://prismlauncher.org)** (Windows : le réveil du serveur passe par PowerShell).
2. **Ajouter son compte** : *Comptes* → *Gérer les comptes* → *Ajouter Microsoft*.
3. **Importer l'instance** de son serveur (tableau ci-dessous) : *Ajouter une instance* → *Importer* → le zip téléchargé.
4. **Lancer l'instance.** Si le serveur dormait, il se réveille pendant le chargement (de quelques secondes
   à 2 minutes), puis le jeu s'y connecte tout seul.

## Les serveurs

<!-- sommaire -->

| Serveur | Adresse | Contenu | Mis à jour | Instance Prism |
|---|---|---|---|---|
| **captive25** | `captive25.tomz.fr` | Minecraft 1.21.10 · serveur de plugins : les plugins sont sur le serveur, rien à installer de plus | [07/10/2026](https://github.com/Tomzmn/Modpack/commits/main/captive25) | [captive25.zip](https://github.com/Tomzmn/Modpack/releases/download/instance-captive25/captive25.zip) |
| **jarry20** | `jarry20.tomz.fr` | Minecraft 1.15.2 · serveur de plugins : les plugins sont sur le serveur, rien à installer de plus | [07/10/2026](https://github.com/Tomzmn/Modpack/commits/main/jarry20) | [jarry20.zip](https://github.com/Tomzmn/Modpack/releases/download/instance-jarry20/jarry20.zip) |
| **jarry26** | `jarry26.tomz.fr` | Minecraft 1.21.1 · NeoForge 21.1.255 · 25 mods | [05/10/2026](https://github.com/Tomzmn/Modpack/commits/main/jarry26) | [jarry26.zip](https://github.com/Tomzmn/Modpack/releases/download/instance-jarry26/jarry26.zip) |
| **luc25** | `luc25.tomz.fr` | Minecraft 1.21.4 · serveur de plugins : les plugins sont sur le serveur, rien à installer de plus | [07/10/2026](https://github.com/Tomzmn/Modpack/commits/main/luc25) | [luc25.zip](https://github.com/Tomzmn/Modpack/releases/download/instance-luc25/luc25.zip) |
| **noah25** | `noah25.tomz.fr` | Minecraft 1.20.1 · Forge 47.4.20 · 153 mods | [04/10/2026](https://github.com/Tomzmn/Modpack/commits/main/noah25) | [noah25.zip](https://github.com/Tomzmn/Modpack/releases/download/instance-noah25/noah25.zip) |
| **noah26** | `noah26.tomz.fr` | Minecraft 1.20.1 · Forge 47.4.20 · 151 mods · 3 shaders | [05/10/2026](https://github.com/Tomzmn/Modpack/commits/main/noah26) | [noah26.zip](https://github.com/Tomzmn/Modpack/releases/download/instance-noah26/noah26.zip) |
| **remy19** | `remy19.tomz.fr` | Minecraft 1.21.10 · serveur de plugins : les plugins sont sur le serveur, rien à installer de plus | [07/10/2026](https://github.com/Tomzmn/Modpack/commits/main/remy19) | [remy19.zip](https://github.com/Tomzmn/Modpack/releases/download/instance-remy19/remy19.zip) |
| **remy20** | `remy20.tomz.fr` | Minecraft 1.21.10 · serveur de plugins : les plugins sont sur le serveur, rien à installer de plus | [07/10/2026](https://github.com/Tomzmn/Modpack/commits/main/remy20) | [remy20.zip](https://github.com/Tomzmn/Modpack/releases/download/instance-remy20/remy20.zip) |
| **tom20** | hors du proxy | Minecraft 1.7.10 · 15 plugins | [04/10/2026](https://github.com/Tomzmn/Modpack/commits/main/tom20) | [tom20.zip](https://github.com/Tomzmn/Modpack/releases/download/instance-tom20/tom20.zip) |
| **tomwe20** | hors du proxy | Minecraft 1.7.10 · serveur de plugins : les plugins sont sur le serveur, rien à installer de plus | [07/10/2026](https://github.com/Tomzmn/Modpack/commits/main/tomwe20) | [tomwe20.zip](https://github.com/Tomzmn/Modpack/releases/download/instance-tomwe20/tomwe20.zip) |

<!-- /sommaire -->

## Bon à savoir

- **Il n'existe qu'une version de chaque pack, la dernière**, et l'instance s'y met à jour à chaque
  lancement : inutile de re-télécharger le zip quand le pack change, il ne sert qu'à la première installation.
- **Ce qui a changé** : la date « Mis à jour » du tableau mène à l'historique du pack.
- **Le serveur ne répond pas ?** Relancer l'instance : le lancement redemande au serveur de démarrer.
- **Pour les mainteneurs** : un dossier par serveur, au format [packwiz](https://packwiz.infra.link) ; chaque
  changement est un commit sur `main`, que suivent joueurs et serveurs. Le zip d'une instance n'est refait que
  si l'instance elle-même change (version de Minecraft ou du loader, réglages).
