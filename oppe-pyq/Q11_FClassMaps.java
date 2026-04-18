import java.util.*;

/**
 * QUESTION: Maps - Cricket Team (Sep 2024 OPPE1, Session 1 Type 4)
 * ============================================================================
 * Problem Statement:
 * The Java program below takes as input the names of cricket players in a team
 * and the runs scored by each of them in 3 consecutive matches. The program is
 * supposed to print the names of those players who have scored at least 80 runs
 * in ALL the matches.
 *
 * (Same structure as Q4 but from Sep 2024 OPPE paper)
 *
 * Class Team has:
 *   - Instance variable: Map<String, ArrayList<Integer>> playerMap
 *   - Constructor to initialize it
 *   - Accessor method: getPlayerMap()
 *
 * Class FClass has:
 *   - Method getFinalList(Team t): returns list of player names with >= 80 in all matches
 *   - main(): reads 3 players (name + 3 runs each), creates Team, prints getFinalList result
 *
 * What you have to do: Define method getFinalList() of class FClass
 *
 * Test Cases:
 *   Input: Ravi 76 76 76 / sonu 80 80 89 / viral 98 47 99  →  Output: [sonu]
 *   Input: P1 79 80 45 / P2 88 46 90 / P3 89 56 21         →  Output: []
 *   Input: P1 82 97 120 / P2 80 90 99 / P3 87 112 145      →  Output: [P1, P2, P3]
 *   Input: P1 23 90 92 / P2 88 65 78 / P3 80 80 80         →  Output: [P3]
 */

class TeamB {
    private Map<String, ArrayList<Integer>> playerMap;
    public TeamB(Map<String, ArrayList<Integer>> m) {
        playerMap = m;
    }
    public Map<String, ArrayList<Integer>> getPlayerMap() {
        return playerMap;
    }
}

public class Q11_FClassMaps {
    // Define the method getFinalList() here
    public static ArrayList<String> getFinalList(TeamB t) {
        ArrayList<String> a=new ArrayList<String>();
        for(var e:t.getPlayerMap().entrySet()){boolean f=true;for(int x:e.getValue())if(x<80)f=false; if(f)a.add(e.getKey());}
        return a;
    }

    public static void main(String[] args) {
        Scanner sc = new Scanner(System.in);
        Map<String, ArrayList<Integer>> pmap =
            new LinkedHashMap<String, ArrayList<Integer>>();
        for (int i = 0; i < 3; i++) {
            ArrayList<Integer> pruns = new ArrayList<Integer>();
            String name = sc.next();
            for (int j = 0; j < 3; j++) {
                pruns.add(sc.nextInt());
            }
            pmap.put(name, pruns);
        }
        TeamB t = new TeamB(pmap);
        System.out.println(getFinalList(t));
    }
}
