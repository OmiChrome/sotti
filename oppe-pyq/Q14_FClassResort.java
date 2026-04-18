import java.util.*;

/**
 * QUESTION: Maps - Resort Ratings (July 2025 OPPE1, Question 3)
 * ============================================================================
 * Problem Statement:
 * Write a Java program that, given as input the names of resorts in a tourist
 * place and the ratings scored by each of them in 3 consecutive months, prints
 * the names of those resorts which have scored at least 4 in ALL the months.
 *
 * Class Place has:
 *   - Private instance variable: Map<String, ArrayList<Integer>> resortMap
 *     (maps resort name to list of ratings per month)
 *   - Constructor to initialize the instance variable
 *   - Accessor method: getResortMap()
 *
 * Class FClass has:
 *   - Method getFinalList(Place p): returns list of resort names with rating >= 4
 *     in all months
 *   - main(): reads 3 resorts (name + 3 ratings each), creates Place object,
 *     calls getFinalList(), prints the result
 *
 * What you have to do: Define method getFinalList() of class FClass
 *
 * (Test cases not provided in the PDF, but structure is same as cricket runs Q4/Q11
 * but with rating >= 4 instead of runs >= 80, and uses Place/resortMap)
 */

class Place {
    private Map<String, ArrayList<Integer>> resortMap;
    public Place(Map<String, ArrayList<Integer>> r) {
        resortMap = r;
    }
    public Map<String, ArrayList<Integer>> getResortMap() {
        return resortMap;
    }
}

public class Q14_FClassResort {
    // Define getFinalList(Place p) here
    public static ArrayList<String> getFinalList(Place p) {
        // YOUR CODE HERE
        return null; // placeholder
    }

    public static void main(String[] args) {
        Scanner sc = new Scanner(System.in);
        Map<String, ArrayList<Integer>> rmap = new LinkedHashMap<String, ArrayList<Integer>>();
        for (int i = 0; i < 3; i++) {
            ArrayList<Integer> ratingList = new ArrayList<Integer>();
            String name = sc.next();
            for (int j = 0; j < 3; j++) {
                ratingList.add(sc.nextInt());
            }
            rmap.put(name, ratingList);
        }
        Place p = new Place(rmap);
        System.out.println(getFinalList(p));
    }
}
